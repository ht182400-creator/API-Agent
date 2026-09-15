"""
出站 URL 安全（SSRF 防护）与权限统一测试

覆盖本轮优化：
1. 出站地址校验 ensure_outbound_url_allowed（协议 / 元数据 / 私网 / 环回）
2. settings 私网出站策略（private_repo_endpoints_allowed / security notices）
3. 管理员权限校验函数统一（auth_service 为唯一实现）
4. 路由去重（无前缀暴露已消除）

用例编号：TC-SSRF-xxx / TC-PERM-xxx / TC-ROUTE-xxx
"""

import pytest

from src.utils.url_safety import (
    OutboundURLBlocked,
    ensure_outbound_url_allowed,
    is_url_allowed,
)


# ==================== 1. 协议与格式校验 ====================

class TestOutboundUrlScheme:
    """协议与格式"""

    def test_empty_url_rejected(self):
        """TC-SSRF-001: 空地址被拒绝"""
        with pytest.raises(OutboundURLBlocked):
            ensure_outbound_url_allowed("")
        with pytest.raises(OutboundURLBlocked):
            ensure_outbound_url_allowed("   ")

    def test_missing_host_rejected(self):
        """TC-SSRF-002: 缺少主机名被拒绝"""
        with pytest.raises(OutboundURLBlocked):
            ensure_outbound_url_allowed("http:///path")

    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "gopher://127.0.0.1:6379/_INFO",
            "ftp://example.com/x",
            "dict://127.0.0.1:11211/stat",
            "ldap://127.0.0.1:389/",
        ],
    )
    def test_non_http_scheme_rejected(self, url):
        """TC-SSRF-003: 非 http/https 协议一律拒绝"""
        with pytest.raises(OutboundURLBlocked):
            ensure_outbound_url_allowed(url, allow_private=True)

    @pytest.mark.parametrize("url", ["http://example.com/api", "https://example.com/api"])
    def test_http_and_https_allowed(self, url):
        """TC-SSRF-004: http/https 正常通过"""
        assert ensure_outbound_url_allowed(url, resolve_dns=False) == url


# ==================== 2. 元数据地址（任何环境都拦截）====================

class TestMetadataAddress:
    """云元数据地址"""

    @pytest.mark.parametrize(
        "url",
        [
            "http://169.254.169.254/latest/meta-data/",
            "http://100.100.100.200/latest/meta-data/",
            "http://[fd00:ec2::254]/latest/meta-data/",
        ],
    )
    def test_metadata_ip_blocked_even_when_private_allowed(self, url):
        """TC-SSRF-005: 元数据地址即使允许私网也必须拦截"""
        with pytest.raises(OutboundURLBlocked):
            ensure_outbound_url_allowed(url, allow_private=True)

    def test_metadata_hostname_blocked(self):
        """TC-SSRF-006: 元数据主机名被拦截"""
        with pytest.raises(OutboundURLBlocked):
            ensure_outbound_url_allowed(
                "http://metadata.google.internal/computeMetadata/v1/",
                allow_private=True,
                resolve_dns=False,
            )


# ==================== 3. 私网 / 环回地址 ====================

class TestPrivateAddressPolicy:
    """私网与环回策略"""

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:8001/weather",
            "http://localhost:8001/weather",
            "http://10.0.0.5/internal",
            "http://192.168.1.10/admin",
            "http://172.16.0.3/x",
            "http://169.254.1.1/x",
            "http://[::1]:8001/x",
        ],
    )
    def test_private_blocked_when_not_allowed(self, url):
        """TC-SSRF-007: 禁止私网时，私网/环回地址被拦截"""
        with pytest.raises(OutboundURLBlocked):
            ensure_outbound_url_allowed(url, allow_private=False)

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:8001/weather",
            "http://localhost:8001/weather",
            "http://10.0.0.5/internal",
        ],
    )
    def test_private_allowed_when_opted_in(self, url):
        """TC-SSRF-008: 显式允许私网时可通过（兼容本地示例 API）"""
        assert ensure_outbound_url_allowed(url, allow_private=True) == url

    def test_localhost_subdomain_blocked(self):
        """TC-SSRF-009: *.localhost 一律拦截（即使允许私网）"""
        with pytest.raises(OutboundURLBlocked):
            ensure_outbound_url_allowed(
                "http://api.localhost:8001/x",
                allow_private=True,
                resolve_dns=False,
            )

    def test_is_url_allowed_helper(self):
        """TC-SSRF-010: is_url_allowed 便捷判断"""
        assert is_url_allowed("http://127.0.0.1:8001/x", allow_private=True) is True
        assert is_url_allowed("http://127.0.0.1:8001/x", allow_private=False) is False
        assert is_url_allowed("file:///etc/passwd", allow_private=True) is False


# ==================== 4. settings 私网出站策略 ====================

class TestPrivateEndpointSetting:
    """settings 策略联动"""

    def test_default_follows_environment(self):
        """TC-SSRF-011: 未显式配置时，非生产允许、生产禁止"""
        from src.config.settings import Settings

        assert Settings(environment="development").private_repo_endpoints_allowed is True
        assert Settings(environment="staging").private_repo_endpoints_allowed is True
        assert Settings(environment="production").private_repo_endpoints_allowed is False

    def test_explicit_override(self):
        """TC-SSRF-012: 显式配置优先于环境推断"""
        from src.config.settings import Settings

        assert Settings(
            environment="production", allow_private_repo_endpoints=True
        ).private_repo_endpoints_allowed is True
        assert Settings(
            environment="development", allow_private_repo_endpoints=False
        ).private_repo_endpoints_allowed is False

    def test_security_notice_on_production_opt_in(self):
        """TC-SSRF-013: 生产环境显式放行私网时给出安全提示（非致命）"""
        from src.config.settings import Settings

        s = Settings(
            environment="production",
            payment_mock_mode=False,
            alipay_sandbox=False,
            debug=False,
            allow_private_repo_endpoints=True,
        )
        notices = s.collect_security_notices()
        assert notices and "SSRF" in notices[0]

    def test_no_notice_by_default(self):
        """TC-SSRF-014: 默认（生产禁止私网）无安全提示"""
        from src.config.settings import Settings

        assert Settings(environment="production").collect_security_notices() == []
        assert Settings(environment="development").collect_security_notices() == []


# ==================== 5. 权限校验函数统一 ====================

class _FakeUser:
    """权限判定用的轻量用户对象（PermissionService 仅读取 user_type/role/permissions）"""

    def __init__(self, user_type: str, role: str = None, permissions=None):
        self.user_type = user_type
        self.role = role
        self.permissions = permissions or []


class TestPermissionUnification:
    """管理员权限校验统一"""

    def test_single_implementation(self):
        """TC-PERM-001: 各模块共用 auth_service 中的唯一实现"""
        from src.services.auth_service import check_admin_permission as canonical
        from src.api.v1 import repositories as repo_mod
        from src.api.v1 import analytics as ana_mod

        assert repo_mod.check_admin_permission is canonical
        assert ana_mod.check_admin_permission is canonical

    @pytest.mark.parametrize("user_type", ["admin", "super_admin"])
    def test_admin_passes(self, user_type):
        """TC-PERM-002: 管理员与超级管理员通过校验"""
        from src.services.auth_service import check_admin_permission

        check_admin_permission(_FakeUser(user_type=user_type))  # 不抛异常

    @pytest.mark.parametrize("user_type", ["developer", "user", "owner"])
    def test_non_admin_rejected(self, user_type):
        """TC-PERM-003: 非管理员被拒绝（AuthorizationError）"""
        from src.core.exceptions import AuthorizationError
        from src.services.auth_service import check_admin_permission

        with pytest.raises(AuthorizationError):
            check_admin_permission(_FakeUser(user_type=user_type))


# ==================== 6. 路由去重（无前缀暴露已消除）====================

class TestRouteDeduplication:
    """路由注册去重（需要应用与数据库，属集成用例）"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", ["/api/v1/files", "/api/v1/content", "/api/v1/backups"])
    async def test_no_prefixless_admin_log_exposure(self, client, path):
        """TC-ROUTE-001: 管理日志接口不再以无前缀形式暴露（应为 404）"""
        resp = await client.get(path)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_admin_log_route_still_available(self, client):
        """TC-ROUTE-002: 正确路径 /admin/logs/* 仍然存在（未登录返回 401）"""
        resp = await client.get("/api/v1/admin/logs/content", params={"file_path": "x.log"})
        assert resp.status_code == 401
