"""
支付回调来源 IP 白名单测试

背景（2026-09-15 新增）：
    支付回调接口（/payments/alipay/callback 与 /payments/callback）原先仅有
    验签/令牌门控，无来源 IP 级控制。现增加可选白名单：
    - 配置 `PAYMENT_CALLBACK_IP_ALLOWLIST`（逗号分隔 IP/CIDR）→ 直连来源不在名单内 403；
    - 未配置/为空 → 校验关闭（保持既有部署行为，零回归）；
    - 安全校验只基于**直连 IP**（request.client.host），不信任可伪造的 X-Forwarded-For。

用例编号：TC-IP-001 ~ TC-IP-009
"""

import pytest

from src.config.settings import settings as global_settings
from src.utils.helpers import is_ip_allowed

# ==================== 1. is_ip_allowed 单元测试 ====================


class TestIsIpAllowed:
    def test_allowlist_disabled_allows_everything(self):
        """TC-IP-001: 白名单未配置/空 = 校验关闭，一律放行（含 unknown）"""
        for allowlist in (None, "", "   "):
            assert is_ip_allowed("1.2.3.4", allowlist) is True
            assert is_ip_allowed(None, allowlist) is True
            assert is_ip_allowed("unknown", allowlist) is True

    def test_exact_ip_match(self):
        """TC-IP-002: 精确 IP 命中 / 不命中"""
        allowlist = "110.75.8.1,203.0.113.7"
        assert is_ip_allowed("110.75.8.1", allowlist) is True
        assert is_ip_allowed("203.0.113.7", allowlist) is True
        assert is_ip_allowed("110.75.8.2", allowlist) is False

    def test_cidr_match(self):
        """TC-IP-003: CIDR 网段命中（IPv4 与 IPv6）"""
        allowlist = "110.75.0.0/16,2001:db8::/32"
        assert is_ip_allowed("110.75.8.1", allowlist) is True
        assert is_ip_allowed("110.76.0.1", allowlist) is False
        assert is_ip_allowed("2001:db8::1", allowlist) is True
        assert is_ip_allowed("2001:db9::1", allowlist) is False

    def test_fail_closed(self):
        """TC-IP-004: fail-closed —— 来源未知/非法、网段配置非法时不放行"""
        allowlist = "110.75.0.0/16"
        assert is_ip_allowed(None, allowlist) is False           # 来源缺失
        assert is_ip_allowed("unknown", allowlist) is False      # 来源未知
        assert is_ip_allowed("not-an-ip", allowlist) is False    # 非法 IP
        # 非法网段条目被跳过，不影响其它条目判定
        assert is_ip_allowed("110.75.8.1", "bad-cidr,110.75.0.0/16") is True
        assert is_ip_allowed("1.2.3.4", "bad-cidr,110.75.0.0/16") is False

    def test_mixed_entries_with_spaces(self):
        """TC-IP-005: 多条目 + 空白容错"""
        allowlist = " 110.75.0.0/16 , 203.0.113.7 , "
        assert is_ip_allowed("110.75.1.1", allowlist) is True
        assert is_ip_allowed("203.0.113.7", allowlist) is True
        assert is_ip_allowed("8.8.8.8", allowlist) is False


# ==================== 2. 回调接口集成测试（403 拒绝 / 默认放行） ====================


class TestCallbackEndpointsAllowlist:
    # httpx ASGITransport 的直连地址为 ("testclient", ...) → host="testclient"
    # 属"非法 IP"，天然满足 fail-closed 路径（白名单开启时必被拒）。
    @pytest.mark.asyncio
    async def test_alipay_callback_rejected_when_allowlist_set(self, client, monkeypatch):
        """TC-IP-006: /alipay/callback —— 白名单开启且来源不在名单 → 403"""
        from src.main import app

        monkeypatch.setattr(
            global_settings, "payment_callback_ip_allowlist", "10.0.0.0/8", raising=False
        )
        resp = await client.post("/api/v1/payments/alipay/callback")

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_alipay_callback_passes_when_allowlist_disabled(self, client, monkeypatch):
        """TC-IP-007: /alipay/callback —— 白名单未配置（默认）→ 放行进入验签流程"""
        monkeypatch.setattr(
            global_settings, "payment_callback_ip_allowlist", "", raising=False
        )
        resp = await client.post("/api/v1/payments/alipay/callback")

        # 放行的证据：不是 403（后续因缺表单数据/未配置等返回 200 系业务响应）
        assert resp.status_code != 403

    @pytest.mark.asyncio
    async def test_generic_callback_rejected_before_auth_gate(self, client, monkeypatch):
        """TC-IP-008: /callback —— IP 校验位于鉴权门控之前（403 而非 401/404）"""
        from src.main import app

        monkeypatch.setattr(
            global_settings, "payment_callback_ip_allowlist", "10.0.0.0/8", raising=False
        )
        resp = await client.post(
            "/api/v1/payments/callback",
            json={
                "payment_no": "PAY_TEST_0001",
                "transaction_id": "TXN_TEST_0001",
                "status": "success",
            },
        )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_generic_callback_passes_gate_when_allowlist_disabled(
        self, client, monkeypatch
    ):
        """TC-IP-009: /callback —— 白名单关闭时行为与改造前一致（走既有令牌/登录门控）"""
        monkeypatch.setattr(
            global_settings, "payment_callback_ip_allowlist", "", raising=False
        )
        resp = await client.post(
            "/api/v1/payments/callback",
            json={
                "payment_no": "PAY_TEST_0001",
                "transaction_id": "TXN_TEST_0001",
                "status": "success",
            },
        )

        # 无令牌无登录 → 命中既有门控 401（而非 IP 层 403）—— 证明零回归
        assert resp.status_code == 401
