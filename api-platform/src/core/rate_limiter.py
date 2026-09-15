"""
限流器（Redis 优先，进程内内存降级）

背景：
    改造前 API Key 的 RPM/RPH 限流通过 "每次请求都查 APICallLog 计数表" 实现，
    在高并发下会把数据库打满，无法支撑 10,000 QPS 目标（评审项 P0-3）。

方案：
    1. 主链路走 Redis 固定窗口计数（Lua 脚本保证 INCR + EXPIRE 原子性）；
    2. Redis 不可用时：
       - API Key 维度 → 由调用方（AuthService）回落数据库计数（保持既有行为）；
       - IP 维度     → 使用进程内内存计数（单实例近似，避免完全裸奔）。
    3. 固定窗口 vs 滑动窗口：固定窗口实现简单、成本最低，允许窗口边界
       （约 2 倍）突发。对本平台的 RPM/RPH 场景足够，且可避免 ZSET 的高开销。

使用方式：
    result = await check_rate_limit("rpm", f"key:{key_id}", limit=60, window_seconds=60)
    if not result.allowed:
        raise RateLimitError(...)
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from src.config.logging_config import get_logger

logger = get_logger("rate_limit")

# 原子计数脚本：首次自增时设置过期时间
_INCR_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if tonumber(current) == 1 then
    redis.call('PEXPIRE', KEYS[1], ARGV[1])
end
return current
"""


@dataclass
class RateLimitResult:
    """限流判定结果"""

    allowed: bool
    limit: int
    remaining: int
    reset_after: int          # 距离窗口重置的秒数
    current: int              # 当前窗口已计数
    backend: str              # redis / memory / unavailable

    def to_headers(self) -> Dict[str, str]:
        """转换为标准限流响应头"""
        return {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
            "X-RateLimit-Reset": str(self.reset_after),
        }


def _window_bounds(window_seconds: int) -> Tuple[int, int]:
    """
    计算当前固定窗口编号与重置剩余秒数。

    Returns:
        (window_id, reset_after)
    """
    now = int(time.time())
    window_id = now // window_seconds
    reset_after = window_seconds - (now % window_seconds)
    return window_id, reset_after


class RedisRateLimiter:
    """基于 Redis 的固定窗口限流器"""

    _script = None

    @classmethod
    async def _get_script(cls, client):
        if cls._script is None:
            cls._script = client.register_script(_INCR_SCRIPT)
        return cls._script

    @classmethod
    async def check(
        cls,
        scope: str,
        identifier: str,
        limit: int,
        window_seconds: int,
        *,
        prefix: str = "rl",
    ) -> Optional[RateLimitResult]:
        """
        执行一次限流判定（计数 +1）。

        Args:
            scope: 限流维度标识，如 "rpm" / "rph" / "ip"
            identifier: 维度取值，如 API Key ID、客户端 IP
            limit: 窗口内允许的最大次数（<=0 表示不限流）
            window_seconds: 窗口大小（秒）
            prefix: Redis key 前缀

        Returns:
            RateLimitResult；Redis 不可用时返回 None（由调用方决定降级策略）
        """
        if limit is None or limit <= 0:
            return RateLimitResult(
                allowed=True,
                limit=0,
                remaining=0,
                reset_after=0,
                current=0,
                backend="redis",
            )

        from src.core.redis_manager import RedisManager

        client = await RedisManager.get_client()
        if client is None:
            return None

        from src.config.settings import settings

        window_id, reset_after = _window_bounds(window_seconds)
        cache_key = f"{prefix}:{scope}:{identifier}:{window_id}"

        try:
            script = await cls._get_script(client)
            current = await script(keys=[cache_key], args=[window_seconds * 1000])
            current = int(current)
        except Exception as exc:
            RedisManager.mark_unavailable(exc)
            return None

        remaining = limit - current
        allowed = current <= limit

        if not allowed:
            logger.warning(
                "[RateLimit] 触发限流 scope=%s id=%s current=%s limit=%s window=%ss",
                scope,
                identifier,
                current,
                limit,
                window_seconds,
            )

        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            reset_after=reset_after,
            current=current,
            backend="redis",
        )


class InMemoryRateLimiter:
    """
    进程内固定窗口限流器（Redis 不可用时的降级方案）

    局限：仅在单实例内生效，多实例部署下实际限额会被放大，
          因此它只是"不完全裸奔"的兜底，不能替代 Redis。
    """

    _buckets: Dict[str, Tuple[int, int]] = {}
    _lock = asyncio.Lock()

    @classmethod
    async def check(
        cls,
        scope: str,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        if limit is None or limit <= 0:
            return RateLimitResult(
                allowed=True, limit=0, remaining=0, reset_after=0, current=0, backend="memory"
            )

        window_id, reset_after = _window_bounds(window_seconds)
        key = f"{scope}:{identifier}"

        async with cls._lock:
            bucket_window, count = cls._buckets.get(key, (window_id, 0))
            if bucket_window != window_id:
                bucket_window, count = window_id, 0
            count += 1
            cls._buckets[key] = (bucket_window, count)

            # 机会式清理，避免字典无限增长
            if len(cls._buckets) > 10000:
                cls._buckets = {
                    k: v for k, v in cls._buckets.items() if v[0] == window_id
                }

        return RateLimitResult(
            allowed=count <= limit,
            limit=limit,
            remaining=limit - count,
            reset_after=reset_after,
            current=count,
            backend="memory",
        )

    @classmethod
    def reset(cls) -> None:
        """清空计数（测试用）"""
        cls._buckets.clear()


async def check_rate_limit(
    scope: str,
    identifier: str,
    limit: int,
    window_seconds: int,
    *,
    prefix: str = "rl",
) -> RateLimitResult:
    """
    统一限流入口：Redis 优先，不可用时降级为进程内内存计数。

    Args:
        scope: 维度标识
        identifier: 维度取值
        limit: 窗口内最大次数
        window_seconds: 窗口大小（秒）
        prefix: Redis key 前缀

    Returns:
        RateLimitResult（backend 字段标明实际使用的后端）
    """
    from src.config.settings import settings

    if settings.rate_limit_backend == "redis":
        result = await RedisRateLimiter.check(
            scope, identifier, limit, window_seconds, prefix=prefix
        )
        if result is not None:
            return result

    return await InMemoryRateLimiter.check(scope, identifier, limit, window_seconds)
