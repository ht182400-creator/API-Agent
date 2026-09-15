"""
仓库后端地址写入侧校验（N-1）与就绪探针（N-8）测试

覆盖：
1. `_validate_endpoint_url` 写入侧 SSRF 校验（创建/更新仓库时拦截非法地址）
2. `/ready` 就绪探针（区分存活探针 /health）

用例编号：TC-REPO-URL-xxx / TC-READY-xxx
"""

import pytest
from fastapi import HTTPException

from src.api.v1.repositories import _validate_endpoint_url


# ==================== 1. 写入侧地址校验（N-1）====================

class TestValidateEndpointUrl:
    """仓库后端地址写入侧校验"""

    def test_empty_returns_none(self):
        """TC-REPO-URL-001: 未配置后端地址时返回 None"""
        assert _validate_endpoint_url(None) is None
        assert _validate_endpoint_url("") is None
        assert _validate_endpoint_url("   ") is None

    def test_valid_https_returns_stripped(self):
        """TC-REPO-URL-002: 合法地址返回并去除首尾空白"""
        assert (
            _validate_endpoint_url("  https://8.8.8.8/v1  ")
            == "https://8.8.8.8/v1"
        )

    def test_valid_http_allowed(self):
        """TC-REPO-URL-003: http 协议合法

        说明：这里使用公网 IP 字面量，避免依赖测试环境的 DNS 解析能力
              （域名无法解析时会按 fail-closed 策略被拒绝）。
        """
        assert _validate_endpoint_url("http://8.8.8.8") == "http://8.8.8.8"

    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "gopher://127.0.0.1:6379/_INFO",
            "ftp://example.com/x",
        ],
    )
    def test_illegal_scheme_rejected(self, url):
        """TC-REPO-URL-004: 非 http/https 协议被拒绝（400）"""
        with pytest.raises(HTTPException) as exc:
            _validate_endpoint_url(url)
        assert exc.value.status_code == 400

    @pytest.mark.parametrize(
        "url",
        [
            "http://169.254.169.254/latest/meta-data/",
            "http://100.100.100.200/latest/meta-data/",
        ],
    )
    def test_metadata_address_rejected(self, url):
        """TC-REPO-URL-005: 云元数据地址被拒绝（即使允许私网）"""
        with pytest.raises(HTTPException) as exc:
            _validate_endpoint_url(url)
        assert exc.value.status_code == 400
        assert "不被允许" in exc.value.detail

    def test_private_address_follows_policy(self, monkeypatch):
        """TC-REPO-URL-006: 私网地址按策略放行/拦截"""
        from src.config.settings import settings

        # 禁止私网 → 拒绝
        monkeypatch.setattr(settings, "allow_private_repo_endpoints", False, raising=False)
        with pytest.raises(HTTPException) as exc:
            _validate_endpoint_url("http://127.0.0.1:8001/weather")
        assert exc.value.status_code == 400

        # 允许私网 → 通过（兼容本地示例 API）
        monkeypatch.setattr(settings, "allow_private_repo_endpoints", True, raising=False)
        assert (
            _validate_endpoint_url("http://127.0.0.1:8001/weather")
            == "http://127.0.0.1:8001/weather"
        )

    def test_error_detail_is_actionable(self):
        """TC-REPO-URL-007: 错误信息包含可操作提示"""
        with pytest.raises(HTTPException) as exc:
            _validate_endpoint_url("file:///tmp/x")
        assert "仓库后端地址不被允许" in exc.value.detail


# ==================== 2. 就绪探针（N-8）====================

class _BrokenConnection:
    """模拟数据库不可用的连接上下文"""

    async def __aenter__(self):
        raise RuntimeError("database unavailable")

    async def __aexit__(self, *exc_info):
        return False


class _BrokenEngine:
    """模拟数据库不可用的引擎"""

    def connect(self):
        return _BrokenConnection()


class TestReadinessProbe:
    """就绪探针"""

    @pytest.mark.asyncio
    async def test_ready_returns_200_when_db_up(self, client, test_engine, monkeypatch):
        """TC-READY-001: 数据库可用时就绪（200）"""
        # /ready 内部直接使用 src.config.database.async_engine，此处替换为测试引擎
        import src.config.database as db_module

        monkeypatch.setattr(db_module, "async_engine", test_engine)

        resp = await client.get("/ready")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body["checks"]["database"]["status"] == "up"
        assert body["checks"]["database"]["required"] is True
        assert "redis" in body["checks"]

    @pytest.mark.asyncio
    async def test_ready_returns_503_when_db_down(self, client, monkeypatch):
        """TC-READY-002: 数据库不可用时就绪失败（503）"""
        import src.config.database as db_module

        monkeypatch.setattr(db_module, "async_engine", _BrokenEngine())

        resp = await client.get("/ready")

        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "not_ready"
        assert body["checks"]["database"]["status"] == "down"
        assert "error" in body["checks"]["database"]

    @pytest.mark.asyncio
    async def test_redis_is_not_required_by_default(self, client, test_engine, monkeypatch):
        """TC-READY-003: Redis 默认非强依赖（不因 Redis 抖动摘除实例）"""
        import src.config.database as db_module
        from src.config.settings import settings

        monkeypatch.setattr(db_module, "async_engine", test_engine)

        resp = await client.get("/ready")
        body = resp.json()

        assert body["checks"]["redis"]["required"] is settings.ready_require_redis
        if not settings.ready_require_redis:
            assert body["status"] == "ready"    # redis 可能 down，但不影响就绪

    @pytest.mark.asyncio
    async def test_health_still_alive_only(self, client):
        """TC-READY-004: /health 为存活探针，不校验依赖"""
        resp = await client.get("/health")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert "checks" not in body

    def test_ready_is_rate_limit_exempt(self):
        """TC-READY-005: /ready 默认免限流（避免探针被限流摘除）"""
        from src.config.settings import Settings

        assert "/ready" in Settings().rate_limit_exempt_path_list
