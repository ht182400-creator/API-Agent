"""
限流（Redis 优先 + 内存降级）测试 —— 评审项 P0-3

覆盖：
1. 进程内固定窗口限流器（InMemoryRateLimiter）
2. Redis 固定窗口限流器（RedisRateLimiter，使用假客户端）
3. 统一入口 check_rate_limit 的后端选择
4. IP 维度限流中间件（含 429 响应与响应头）
5. 相关配置项默认值与解析

用例编号：TC-RL-xxx
"""

import time

import pytest

from src.core.rate_limiter import (
    InMemoryRateLimiter,
    RateLimitResult,
    RedisRateLimiter,
    check_rate_limit,
)
from src.core.redis_manager import RedisManager


@pytest.fixture(autouse=True)
def _reset_limiters():
    """每个用例前后重置限流器状态，避免相互污染"""
    InMemoryRateLimiter.reset()
    RedisRateLimiter._script = None
    RedisManager._unavailable_until = 0.0
    yield
    InMemoryRateLimiter.reset()
    RedisRateLimiter._script = None
    RedisManager._unavailable_until = 0.0


# ==================== 1. 进程内限流器 ====================

class TestInMemoryRateLimiter:
    """进程内固定窗口限流器"""

    @pytest.mark.asyncio
    async def test_allows_up_to_limit(self):
        """TC-RL-001: 限额内放行"""
        for i in range(3):
            result = await InMemoryRateLimiter.check("rpm", "k1", limit=3, window_seconds=60)
            assert result.allowed is True, f"第 {i+1} 次应放行"
            assert result.remaining == 2 - i
            assert result.backend == "memory"

    @pytest.mark.asyncio
    async def test_blocks_over_limit(self):
        """TC-RL-002: 超出限额被拒绝"""
        for _ in range(3):
            await InMemoryRateLimiter.check("rpm", "k2", limit=3, window_seconds=60)

        result = await InMemoryRateLimiter.check("rpm", "k2", limit=3, window_seconds=60)
        assert result.allowed is False
        assert result.current == 4
        assert result.remaining == -1

    @pytest.mark.asyncio
    async def test_identifiers_are_isolated(self):
        """TC-RL-003: 不同标识互不影响"""
        await InMemoryRateLimiter.check("rpm", "a", limit=1, window_seconds=60)
        blocked = await InMemoryRateLimiter.check("rpm", "a", limit=1, window_seconds=60)
        other = await InMemoryRateLimiter.check("rpm", "b", limit=1, window_seconds=60)

        assert blocked.allowed is False
        assert other.allowed is True

    @pytest.mark.asyncio
    async def test_zero_limit_means_unlimited(self):
        """TC-RL-004: limit<=0 表示不限流"""
        result = await InMemoryRateLimiter.check("rpm", "k3", limit=0, window_seconds=60)
        assert result.allowed is True
        assert result.limit == 0

    @pytest.mark.asyncio
    async def test_window_rollover_resets(self):
        """TC-RL-005: 窗口切换后计数重置"""
        # 使用 1 秒窗口，等待窗口滚动
        first = await InMemoryRateLimiter.check("rpm", "k4", limit=1, window_seconds=1)
        second = await InMemoryRateLimiter.check("rpm", "k4", limit=1, window_seconds=1)
        assert first.allowed is True
        assert second.allowed is False

        time.sleep(1.2)
        third = await InMemoryRateLimiter.check("rpm", "k4", limit=1, window_seconds=1)
        assert third.allowed is True


# ==================== 2. Redis 限流器（假客户端） ====================

class _FakeRedis:
    """最小可用的假 Redis 客户端（模拟 Lua 计数脚本）"""

    def __init__(self, fail: bool = False):
        self.counters = {}
        self.fail = fail
        self.last_key = None

    def register_script(self, script):
        assert "INCR" in script, "应使用 INCR 实现计数"

        async def _run(keys=None, args=None):
            if self.fail:
                raise RuntimeError("redis connection lost")
            key = keys[0]
            self.last_key = key
            self.counters[key] = self.counters.get(key, 0) + 1
            return self.counters[key]

        return _run


def _patch_redis(monkeypatch, fake: _FakeRedis):
    async def _get_client():
        return fake

    monkeypatch.setattr(RedisManager, "get_client", classmethod(lambda cls: _get_client()))


class TestRedisRateLimiter:
    """Redis 限流器"""

    @pytest.mark.asyncio
    async def test_counts_and_blocks(self, monkeypatch):
        """TC-RL-006: Redis 计数正确并正确拦截"""
        fake = _FakeRedis()
        _patch_redis(monkeypatch, fake)

        for i in range(2):
            result = await RedisRateLimiter.check("rpm", "key-1", limit=2, window_seconds=60)
            assert result is not None
            assert result.allowed is True
            assert result.backend == "redis"

        result = await RedisRateLimiter.check("rpm", "key-1", limit=2, window_seconds=60)
        assert result.allowed is False
        assert result.current == 3

    @pytest.mark.asyncio
    async def test_key_format_includes_prefix_scope_id(self, monkeypatch):
        """TC-RL-007: Redis key 结构包含前缀/维度/标识/窗口"""
        fake = _FakeRedis()
        _patch_redis(monkeypatch, fake)

        await RedisRateLimiter.check(
            "rpm", "abc123", limit=10, window_seconds=60, prefix="myprefix"
        )
        assert fake.last_key.startswith("myprefix:rpm:abc123:")

    @pytest.mark.asyncio
    async def test_returns_none_when_redis_unavailable(self, monkeypatch):
        """TC-RL-008: Redis 异常时返回 None（交由调用方降级）"""
        fake = _FakeRedis(fail=True)
        _patch_redis(monkeypatch, fake)

        result = await RedisRateLimiter.check("rpm", "key-2", limit=10, window_seconds=60)
        assert result is None
        # 同时应进入冷却期，避免持续等待超时
        assert RedisManager._unavailable_until > 0

    @pytest.mark.asyncio
    async def test_no_client_returns_none(self, monkeypatch):
        """TC-RL-009: Redis 未连接时返回 None"""
        async def _none_client():
            return None

        monkeypatch.setattr(RedisManager, "get_client", classmethod(lambda cls: _none_client()))
        result = await RedisRateLimiter.check("rpm", "key-3", limit=10, window_seconds=60)
        assert result is None


# ==================== 3. 统一入口 ====================

class TestCheckRateLimitFacade:
    """check_rate_limit 后端选择"""

    @pytest.mark.asyncio
    async def test_memory_backend(self, monkeypatch):
        """TC-RL-010: 配置 memory 时使用进程内计数"""
        from src.config.settings import settings

        monkeypatch.setattr(settings, "rate_limit_backend", "memory", raising=False)
        result = await check_rate_limit("ip", "1.2.3.4", limit=5, window_seconds=60)
        assert result.backend == "memory"
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_falls_back_to_memory_when_redis_down(self, monkeypatch):
        """TC-RL-011: 配置 redis 但不可用时降级为内存计数"""
        from src.config.settings import settings

        monkeypatch.setattr(settings, "rate_limit_backend", "redis", raising=False)
        fake = _FakeRedis(fail=True)
        _patch_redis(monkeypatch, fake)

        result = await check_rate_limit("ip", "5.6.7.8", limit=5, window_seconds=60)
        assert result.backend == "memory"
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_returns_rate_limit_headers(self):
        """TC-RL-012: 结果可转换为标准限流响应头"""
        result = RateLimitResult(
            allowed=True, limit=10, remaining=7, reset_after=30, current=3, backend="memory"
        )
        headers = result.to_headers()
        assert headers["X-RateLimit-Limit"] == "10"
        assert headers["X-RateLimit-Remaining"] == "7"
        assert headers["X-RateLimit-Reset"] == "30"


# ==================== 4. IP 维度中间件（集成） ====================

class TestIpRateLimitMiddleware:
    """IP 维度限流中间件"""

    @pytest.mark.asyncio
    async def test_disabled_by_default(self, client, monkeypatch):
        """TC-RL-013: 默认关闭时不限流（避免误伤前端 SPA）"""
        from src.config.settings import settings

        monkeypatch.setattr(settings, "rate_limit_ip_enabled", False, raising=False)

        for _ in range(3):
            resp = await client.get("/api/v1/__rate_limit_probe__")
            assert resp.status_code == 404   # 未限流，走到路由未匹配

    @pytest.mark.asyncio
    async def test_enabled_blocks_after_limit(self, client, monkeypatch):
        """TC-RL-014: 开启后超出阈值返回 429（含限流头部）"""
        from src.config.settings import settings

        monkeypatch.setattr(settings, "rate_limit_enabled", True, raising=False)
        monkeypatch.setattr(settings, "rate_limit_ip_enabled", True, raising=False)
        monkeypatch.setattr(settings, "rate_limit_ip_per_minute", 1, raising=False)
        monkeypatch.setattr(settings, "rate_limit_backend", "memory", raising=False)

        first = await client.get("/api/v1/__rate_limit_probe__")
        assert first.status_code == 404

        second = await client.get("/api/v1/__rate_limit_probe__")
        assert second.status_code == 429
        body = second.json()
        assert body["code"] == 42901
        assert body["details"]["scope"] == "ip"
        assert "Retry-After" in second.headers
        assert second.headers["X-RateLimit-Limit"] == "1"

    @pytest.mark.asyncio
    async def test_exempt_paths_bypass(self, client, monkeypatch):
        """TC-RL-015: 免限流路径（/health）不受限流影响"""
        from src.config.settings import settings

        monkeypatch.setattr(settings, "rate_limit_ip_enabled", True, raising=False)
        monkeypatch.setattr(settings, "rate_limit_ip_per_minute", 1, raising=False)
        monkeypatch.setattr(settings, "rate_limit_backend", "memory", raising=False)

        for _ in range(3):
            resp = await client.get("/health")
            assert resp.status_code == 200


# ==================== 5. 配置项 ====================

class TestRateLimitSettings:
    """限流相关配置"""

    def test_defaults(self):
        """TC-RL-016: 默认值符合预期"""
        from src.config.settings import Settings

        s = Settings()
        assert s.rate_limit_backend == "redis"
        assert s.rate_limit_enabled is True
        assert s.rate_limit_ip_enabled is False       # 默认不开启 IP 限流
        assert s.rate_limit_ip_per_minute > 0

    def test_backend_validation(self):
        """TC-RL-017: 非法后端值回落为 redis"""
        from src.config.settings import Settings

        assert Settings(rate_limit_backend="redis").rate_limit_backend == "redis"
        assert Settings(rate_limit_backend="MEMORY").rate_limit_backend == "memory"
        assert Settings(rate_limit_backend="bogus").rate_limit_backend == "redis"

    def test_exempt_path_list(self):
        """TC-RL-018: 免限流路径解析"""
        from src.config.settings import Settings

        s = Settings(rate_limit_exempt_paths="/health, /docs ,,")
        assert s.rate_limit_exempt_path_list == ["/health", "/docs"]
