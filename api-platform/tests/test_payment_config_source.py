"""
支付配置双源收敛测试 —— settings.payment_mock_mode 为唯一权威源

背景（2026-09-15 收敛）：
    原 `system_configs("payment","mock_mode")` 与 `settings.payment_mock_mode` 双数据源：
    - 管理后台改 mock_mode 只写 DB，实际支付行为（payment.py 读 settings）**不变** → 假开关；
    - `admin_payment_config.py` 的 GET /status 读 key="mock_mode"、GET /detail 读
      key="payment.mock_mode"，两行数据可能不一致；
    - settings 侧承担启动 fail-fast 校验、启动横幅、回调门控 —— 权威性无争议。

    收敛后：GET 两接口显示 settings 实际生效值；PUT 修改 mock_mode → 400 拒绝并指引改 .env。

用例编号：TC-PSRC-001 ~ TC-PSRC-004
"""

import pytest

from src.config.settings import settings as global_settings

ROUTER_PREFIX = "/api/v1/admin/payment-config"


async def _override_admin(app):
    """绕过管理员鉴权（本组用例聚焦配置源一致性，鉴权由其它用例覆盖）"""
    from src.services.auth_service import get_current_admin_user

    app.dependency_overrides[get_current_admin_user] = lambda: {"username": "tester"}


async def _clear_override(app):
    from src.services.auth_service import get_current_admin_user

    app.dependency_overrides.pop(get_current_admin_user, None)


@pytest.fixture
def patched_mock_mode(monkeypatch):
    """将全局 settings.payment_mock_mode 置为已知值（测试结束自动恢复）"""
    monkeypatch.setattr(global_settings, "payment_mock_mode", True, raising=False)
    return global_settings


class TestPaymentConfigSingleSource:
    @pytest.mark.asyncio
    async def test_status_reports_settings_mock_mode(self, client, patched_mock_mode):
        """TC-PSRC-001: GET /status 显示 settings 的实际生效值（而非 DB 镜像）"""
        from src.main import app

        await _override_admin(app)
        try:
            resp = await client.get(f"{ROUTER_PREFIX}/status")

            assert resp.status_code == 200
            assert resp.json()["data"]["mock_mode"] == patched_mock_mode.payment_mock_mode
        finally:
            await _clear_override(app)

    @pytest.mark.asyncio
    async def test_status_follows_settings_change(self, client, monkeypatch):
        """TC-PSRC-002: settings 值变化时 /status 跟随（证明读的是同一权威源）"""
        from src.main import app

        monkeypatch.setattr(global_settings, "payment_mock_mode", False, raising=False)
        await _override_admin(app)
        try:
            resp = await client.get(f"{ROUTER_PREFIX}/status")

            assert resp.status_code == 200
            assert resp.json()["data"]["mock_mode"] is False
        finally:
            await _clear_override(app)

    @pytest.mark.asyncio
    async def test_detail_reports_settings_mock_mode(self, client, patched_mock_mode):
        """TC-PSRC-003: GET /detail 与 /status 口径一致（原两接口读取 key 不一致）"""
        from src.main import app

        await _override_admin(app)
        try:
            resp = await client.get(f"{ROUTER_PREFIX}/detail")

            assert resp.status_code == 200
            assert resp.json()["data"]["mock_mode"] == patched_mock_mode.payment_mock_mode
        finally:
            await _clear_override(app)

    @pytest.mark.asyncio
    async def test_update_mock_mode_rejected(self, client, patched_mock_mode):
        """TC-PSRC-004: PUT 修改 mock_mode（与当前值不同）→ 400 拒绝，且不写 DB"""
        from src.main import app

        await _override_admin(app)
        try:
            target = not patched_mock_mode.payment_mock_mode
            resp = await client.put(
                f"{ROUTER_PREFIX}/update", json={"mock_mode": target}
            )

            assert resp.status_code == 400
            body = resp.json()
            # 提示信息必须指引正确做法（改 .env），避免管理员再次踩"假开关"坑
            assert "PAYMENT_MOCK_MODE" in str(body)
        finally:
            await _clear_override(app)

    @pytest.mark.asyncio
    async def test_update_same_mock_mode_passes(self, client, patched_mock_mode):
        """TC-PSRC-005: PUT 传入与当前一致的 mock_mode → 幂等放行（200）"""
        from src.main import app

        await _override_admin(app)
        try:
            resp = await client.put(
                f"{ROUTER_PREFIX}/update",
                json={"mock_mode": patched_mock_mode.payment_mock_mode},
            )

            assert resp.status_code == 200
            assert resp.json()["data"]["mock_mode"] == patched_mock_mode.payment_mock_mode
        finally:
            await _clear_override(app)

    def test_default_configs_has_no_mock_mode_seed(self):
        """TC-PSRC-006: 模型不再播种 payment.mock_mode（DB 侧彻底退出权威位）"""
        from src.models.system_config import DEFAULT_CONFIGS

        assert "payment.mock_mode" not in DEFAULT_CONFIGS
