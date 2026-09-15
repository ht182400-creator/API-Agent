"""
缓存工具测试 —— 评审项 P1-5

覆盖：
1. key 命名空间构造
2. 读取 / 写入 / JSON 读写
3. 单 key 删除与前缀批量失效
4. 缓存禁用、Redis 不可用、内容损坏等降级路径

用例编号：TC-CACHE-xxx
"""

import json

import pytest

from src.core import cache as cache_mod
from src.core.redis_manager import RedisManager


class _FakeRedis:
    """最小可用的假 Redis（支持 get/set/delete/scan）"""

    def __init__(self, fail: bool = False):
        self.store = {}
        self.fail = fail

    def _guard(self):
        if self.fail:
            raise RuntimeError("redis down")

    async def get(self, key):
        self._guard()
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self._guard()
        self.store[key] = value
        return True

    async def delete(self, *keys):
        self._guard()
        count = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                count += 1
        return count

    async def scan(self, cursor=0, match=None, count=None):
        self._guard()
        prefix = (match or "").rstrip("*")
        matched = [k for k in self.store if k.startswith(prefix)]
        return 0, matched


def _patch_redis(monkeypatch, fake):
    async def _get_client():
        return fake

    monkeypatch.setattr(RedisManager, "get_client", classmethod(lambda cls: _get_client()))


@pytest.fixture(autouse=True)
def _reset_redis_state():
    RedisManager._unavailable_until = 0.0
    yield
    RedisManager._unavailable_until = 0.0


# ==================== 1. key 构造 ====================

class TestCacheKey:
    """缓存 key 命名空间"""

    def test_make_key_includes_prefix(self):
        """TC-CACHE-001: key 带全局前缀"""
        from src.config.settings import settings

        key = cache_mod.make_key("recharge_packages", "active")
        assert key == f"{settings.cache_key_prefix}:recharge_packages:active"

    def test_make_key_skips_none(self):
        """TC-CACHE-002: None 段被跳过"""
        assert cache_mod.make_key("a", None, "b").endswith(":a:b")


# ==================== 2. 基本读写 ====================

class TestCacheReadWrite:
    """缓存读写"""

    @pytest.mark.asyncio
    async def test_set_and_get(self, monkeypatch):
        """TC-CACHE-003: 写入后可读取"""
        fake = _FakeRedis()
        _patch_redis(monkeypatch, fake)

        assert await cache_mod.cache_set("k1", "v1", ttl=60) is True
        assert await cache_mod.cache_get("k1") == "v1"

    @pytest.mark.asyncio
    async def test_miss_returns_none(self, monkeypatch):
        """TC-CACHE-004: 未命中返回 None"""
        _patch_redis(monkeypatch, _FakeRedis())
        assert await cache_mod.cache_get("not-exists") is None

    @pytest.mark.asyncio
    async def test_json_roundtrip(self, monkeypatch):
        """TC-CACHE-005: JSON 读写保持一致"""
        _patch_redis(monkeypatch, _FakeRedis())

        payload = [{"id": "p1", "price": 9.9}, {"id": "p2", "price": None}]
        assert await cache_mod.cache_set_json("json-key", payload, ttl=60) is True
        assert await cache_mod.cache_get_json("json-key") == payload

    @pytest.mark.asyncio
    async def test_corrupt_json_treated_as_miss(self, monkeypatch):
        """TC-CACHE-006: 缓存内容损坏时视为未命中并删除"""
        fake = _FakeRedis()
        _patch_redis(monkeypatch, fake)
        fake.store["broken"] = "{not-json"

        assert await cache_mod.cache_get_json("broken") is None
        assert "broken" not in fake.store


# ==================== 3. 失效 ====================

class TestCacheInvalidation:
    """缓存失效"""

    @pytest.mark.asyncio
    async def test_delete_single(self, monkeypatch):
        """TC-CACHE-007: 删除单个 key"""
        fake = _FakeRedis()
        _patch_redis(monkeypatch, fake)
        await cache_mod.cache_set("a", "1", ttl=60)

        assert await cache_mod.cache_delete("a") == 1
        assert await cache_mod.cache_get("a") is None

    @pytest.mark.asyncio
    async def test_delete_prefix(self, monkeypatch):
        """TC-CACHE-008: 按前缀批量失效"""
        fake = _FakeRedis()
        _patch_redis(monkeypatch, fake)

        await cache_mod.cache_set("grp:a", "1", ttl=60)
        await cache_mod.cache_set("grp:b", "2", ttl=60)
        await cache_mod.cache_set("other", "3", ttl=60)

        deleted = await cache_mod.cache_delete_prefix("grp:")
        assert deleted == 2
        assert await cache_mod.cache_get("grp:a") is None
        assert await cache_mod.cache_get("other") == "3"


# ==================== 4. 降级路径 ====================

class TestCacheDegradation:
    """缓存不可用时的降级"""

    @pytest.mark.asyncio
    async def test_disabled_cache(self, monkeypatch):
        """TC-CACHE-009: 缓存关闭时不读写"""
        from src.config.settings import settings

        monkeypatch.setattr(settings, "cache_enabled", False, raising=False)

        assert await cache_mod.cache_get("k") is None
        assert await cache_mod.cache_set("k", "v") is False
        assert await cache_mod.cache_delete("k") == 0

    @pytest.mark.asyncio
    async def test_redis_unavailable_is_silent(self, monkeypatch):
        """TC-CACHE-010: Redis 异常时静默降级，不抛异常"""
        fake = _FakeRedis(fail=True)
        _patch_redis(monkeypatch, fake)

        assert await cache_mod.cache_get("k") is None
        assert await cache_mod.cache_set("k", "v") is False
        assert await cache_mod.cache_delete_prefix("k") == 0
        # 应进入冷却期，避免持续等待超时
        assert RedisManager._unavailable_until > 0

    @pytest.mark.asyncio
    async def test_no_client_returns_miss(self, monkeypatch):
        """TC-CACHE-011: Redis 未连接时读写均安全返回"""
        async def _none_client():
            return None

        monkeypatch.setattr(RedisManager, "get_client", classmethod(lambda cls: _none_client()))

        assert await cache_mod.cache_get("k") is None
        assert await cache_mod.cache_set("k", "v") is False

    @pytest.mark.asyncio
    async def test_serialization_failure_skipped(self, monkeypatch):
        """TC-CACHE-012: 无法序列化的对象跳过缓存而不报错"""
        _patch_redis(monkeypatch, _FakeRedis())

        class _NotSerializable:
            def __repr__(self):
                return "<obj>"

        # default=str 已兜底，这里验证不会抛异常
        result = await cache_mod.cache_set_json("obj", {"o": _NotSerializable()})
        assert isinstance(result, bool)
