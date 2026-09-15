"""
Redis 连接管理器（全局单例）

用途：
    - 限流计数（P0-3）
    - 热点数据缓存（P1-5）
    - 分布式锁 / 幂等控制

设计要点：
    1. 懒加载：首次使用时才建立连接，避免导入即连接导致启动失败；
    2. 可用性探测 + 冷却：Redis 不可用时短时间内不再重试，避免每次请求都等超时；
    3. 优雅降级：不可用时调用方自行决定降级策略（如限流回落数据库）；
    4. 生命周期：由 main.py 的 lifespan 负责 close()。
"""

import asyncio
import time
from typing import Optional

from src.config.settings import settings
from src.config.logging_config import get_logger

logger = get_logger("redis")

# Redis 不可用后的冷却时间（秒）——冷却期内直接判定为不可用，避免反复等超时
UNAVAILABLE_COOLDOWN_SECONDS = 30


class RedisManager:
    """Redis 连接单例管理器"""

    _client = None
    _lock = asyncio.Lock()
    _unavailable_until: float = 0.0

    @classmethod
    async def get_client(cls):
        """
        获取 Redis 异步客户端（懒加载）。

        Returns:
            redis.asyncio.Redis 实例；初始化失败返回 None
        """
        if cls._client is not None:
            return cls._client

        # 【冷却期检查】必须在**加锁前**短路：
        #    此前冷却只在 is_available() 生效，而 rate_limiter/cache 直接调用
        #    本方法 → 冷却期内每个请求仍尝试连接、白等 socket_connect_timeout
        #    （2 秒）→ 重复 WARNING 日志 + 接口延迟劣化（2026-09-15 修复）。
        if time.monotonic() < cls._unavailable_until:
            return None

        async with cls._lock:
            # 双重检查：等锁期间可能已被其它协程恢复/标记
            if time.monotonic() < cls._unavailable_until:
                return None
            if cls._client is not None:
                return cls._client
            if cls._client is not None:
                return cls._client

            try:
                from redis.asyncio import Redis, ConnectionPool

                pool = ConnectionPool.from_url(
                    settings.redis_url,
                    max_connections=settings.redis_max_connections,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=3,
                )
                client = Redis(connection_pool=pool)

                # 连接性探测
                await client.ping()

                cls._client = client
                cls._unavailable_until = 0.0
                logger.info("[Redis] 连接成功: %s", _mask_url(settings.redis_url))
            except Exception as exc:
                cls._unavailable_until = time.monotonic() + UNAVAILABLE_COOLDOWN_SECONDS
                logger.warning(
                    "[Redis] 连接失败，%s 秒内不再重试（将走降级逻辑）: %s",
                    UNAVAILABLE_COOLDOWN_SECONDS,
                    exc,
                )
                cls._client = None

            return cls._client

    @classmethod
    async def is_available(cls) -> bool:
        """判断 Redis 当前是否可用（含冷却期短路）"""
        if time.monotonic() < cls._unavailable_until:
            return False
        client = await cls.get_client()
        if client is None:
            return False
        try:
            await client.ping()
            return True
        except Exception as exc:
            cls._unavailable_until = time.monotonic() + UNAVAILABLE_COOLDOWN_SECONDS
            logger.warning("[Redis] 健康检查失败，进入冷却期: %s", exc)
            return False

    @classmethod
    def mark_unavailable(cls, exc: Optional[Exception] = None) -> None:
        """由调用方在遇到 Redis 异常时标记不可用，触发冷却"""
        cls._unavailable_until = time.monotonic() + UNAVAILABLE_COOLDOWN_SECONDS
        if exc is not None:
            logger.warning("[Redis] 标记为不可用（冷却 %s 秒）: %s", UNAVAILABLE_COOLDOWN_SECONDS, exc)

    @classmethod
    async def close(cls) -> None:
        """关闭连接（应用退出时调用）"""
        client = cls._client
        cls._client = None
        if client is not None:
            try:
                await client.aclose()
                logger.info("[Redis] 连接已关闭")
            except Exception as exc:  # pragma: no cover
                logger.warning("[Redis] 关闭连接异常: %s", exc)


def _mask_url(url: str) -> str:
    """隐藏 Redis URL 中的密码，便于安全打印日志"""
    try:
        if "@" in url and "://" in url:
            scheme, rest = url.split("://", 1)
            _, host = rest.split("@", 1)
            return f"{scheme}://***@{host}"
    except Exception:  # pragma: no cover
        pass
    return url


async def get_redis():
    """便捷函数：获取 Redis 客户端（不可用返回 None）"""
    return await RedisManager.get_client()


async def close_redis() -> None:
    """便捷函数：关闭 Redis 连接"""
    await RedisManager.close()
