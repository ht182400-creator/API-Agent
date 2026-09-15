"""
Redis 连接管理器冷却期测试

背景（2026-09-15 用户日志暴露的真实缺陷）：
    冷却检查原先只在 ``is_available()`` 中生效，而 ``rate_limiter`` / ``cache``
    直接调用 ``get_client()`` —— 冷却期内每个请求仍尝试连接、白等
    ``socket_connect_timeout``（2 秒）→ 重复 WARNING 日志 + 接口延迟劣化。

    修复：``get_client()`` 入口（加锁前）短路检查冷却期。
    本组用例验证冷却期对**所有调用路径**生效，防止回归。

用例编号：TC-RED-001 ~ TC-RED-003
"""

import time

import pytest

from src.core.redis_manager import RedisManager, UNAVAILABLE_COOLDOWN_SECONDS


@pytest.fixture(autouse=True)
def _reset_state():
    """用例前后重置单例状态，避免互相污染"""
    RedisManager._client = None
    RedisManager._unavailable_until = 0.0
    yield
    RedisManager._client = None
    RedisManager._unavailable_until = 0.0


class TestCooldown:
    @pytest.mark.asyncio
    async def test_get_client_short_circuits_in_cooldown(self, monkeypatch):
        """TC-RED-001: 冷却期内 get_client() 快速返回 None，不再尝试连接"""
        # 标记进入冷却期（未来 30 秒内视为不可用）
        RedisManager._unavailable_until = time.monotonic() + UNAVAILABLE_COOLDOWN_SECONDS

        # 若冷却失效，真实连接会尝试 2 秒超时并返回非 None / 抛异常；
        # 这里同时用计数器证明"根本没有尝试连接"
        attempts = {"n": 0}

        class _Boom:
            def __init__(self, *a, **k):
                attempts["n"] += 1

            async def ping(self):
                attempts["n"] += 1
                return True

        import src.core.redis_manager as rm
        monkeypatch.setattr(rm.time, "monotonic", time.monotonic)

        import importlib
        redis_asyncio = importlib.import_module("redis.asyncio")
        monkeypatch.setattr(redis_asyncio, "Redis", _Boom, raising=False)

        client = await RedisManager.get_client()

        assert client is None          # 冷却期内直接判定不可用
        assert attempts["n"] == 0      # 未发生任何真实连接尝试

    @pytest.mark.asyncio
    async def test_get_client_retries_after_cooldown_expires(self, monkeypatch):
        """TC-RED-002: 冷却期过后恢复重试（连接失败 → 再进入冷却）

        修订（2026-09-15）：原用例断言 `get_client() is None`，其成立**依赖"本机 Redis 未运行"**
        这一环境事实 —— Redis 一启动该用例即失败（环境耦合，非代码缺陷）。
        现改为显式 monkeypatch 出"连接失败"，使其在 Redis 运行/未运行两种环境下都稳定通过。
        """
        # 把冷却截止时间设在过去 → 视为冷却结束
        RedisManager._unavailable_until = time.monotonic() - 1

        attempts = {"n": 0}

        class _Boom:
            """模拟连接失败：构造计数 + ping 抛异常"""

            def __init__(self, *a, **k):
                attempts["n"] += 1

            async def ping(self):
                raise ConnectionError("模拟 Redis 不可用")

        import importlib
        redis_asyncio = importlib.import_module("redis.asyncio")
        # redis_manager 内部是函数级 `from redis.asyncio import Redis`（延迟导入），
        # 因此 patch 模块属性即可生效
        monkeypatch.setattr(redis_asyncio, "Redis", _Boom, raising=False)

        assert await RedisManager.get_client() is None          # 连接失败 → None
        assert attempts["n"] >= 1                               # "重试"确实发生了
        # 失败后重新进入冷却
        assert RedisManager._unavailable_until > time.monotonic()

    @pytest.mark.asyncio
    async def test_is_available_consistent_with_get_client(self, monkeypatch):
        """TC-RED-003: is_available 与 get_client 在冷却期内行为一致（双入口同源）"""
        RedisManager._unavailable_until = time.monotonic() + UNAVAILABLE_COOLDOWN_SECONDS

        assert await RedisManager.is_available() is False
        assert await RedisManager.get_client() is None
