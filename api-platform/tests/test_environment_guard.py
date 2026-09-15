"""
环境隔离与生产安全门控测试 (V1.0)

覆盖本次"模拟支付/密钥硬编码安全治理"改造：
1. settings 生产环境强校验（fail-fast）
2. 账单环境标识唯一数据源（billing_environment）
3. 环境过滤解析（resolve_environment：默认当前环境 / all 通配 / 非法降级）
4. 环境过滤条件生成（env_match）
5. 支付回调接口门控（生产下线 / 模拟模式需登录或内部令牌）

用例编号：TC-ENV-xxx / TC-PAY-GUARD-xxx
"""

import pytest
from sqlalchemy import true

from src.config.settings import Settings, settings as global_settings
from src.utils.environment import (
    ENVIRONMENT_ALL,
    VALID_ENVIRONMENTS,
    current_environment,
    env_match,
    resolve_environment,
)


# ==================== 1. settings 生产安全校验 ====================

class TestProductionSafetyGuard:
    """settings 生产环境强校验"""

    def test_billing_environment_follows_runtime_environment(self):
        """TC-ENV-001: 账单环境标识由「运行环境」决定，与模拟支付开关解耦"""
        # 非生产（development / staging）→ simulation
        # 注意：关闭 mock 只代表"不放行模拟回调"，并不代表账单属于生产数据
        assert Settings(environment="development", payment_mock_mode=True).billing_environment == "simulation"
        assert Settings(environment="development", payment_mock_mode=False).billing_environment == "simulation"
        assert Settings(environment="staging", payment_mock_mode=False).billing_environment == "simulation"
        # 生产 → production
        assert Settings(environment="production", payment_mock_mode=False).billing_environment == "production"

    def test_is_production_detection(self):
        """TC-ENV-002: 生产环境识别（兼容 production/prod，大小写不敏感）"""
        assert Settings(environment="production").is_production is True
        assert Settings(environment="PROD").is_production is True
        assert Settings(environment="development").is_production is False
        assert Settings(environment="staging").is_production is False

    def test_non_production_skips_strict_validation(self):
        """TC-ENV-003: 非生产环境下校验为 no-op（允许模拟支付）"""
        s = Settings(environment="development", payment_mock_mode=True)
        s.validate_for_production()  # 不应抛异常
        assert s.collect_production_warnings() == []

    def test_production_with_mock_payment_raises(self):
        """TC-ENV-004: 生产环境开启模拟支付 → 拒绝启动"""
        s = Settings(environment="production", payment_mock_mode=True)
        with pytest.raises(RuntimeError) as exc:
            s.validate_for_production()
        assert "PAYMENT_MOCK_MODE" in str(exc.value)

    def test_production_with_alipay_sandbox_raises(self):
        """TC-ENV-005: 生产环境使用沙箱网关 → 拒绝启动"""
        s = Settings(
            environment="production",
            payment_mock_mode=False,
            alipay_sandbox=True,
        )
        with pytest.raises(RuntimeError) as exc:
            s.validate_for_production()
        assert "ALIPAY_SANDBOX" in str(exc.value)

    def test_production_with_default_secrets_raises(self):
        """TC-ENV-006: 生产环境仍使用默认密钥 → 拒绝启动"""
        s = Settings(
            environment="production",
            payment_mock_mode=False,
            alipay_sandbox=False,
            debug=False,
            jwt_secret_key="your-secret-key-change-in-production",
        )
        with pytest.raises(RuntimeError) as exc:
            s.validate_for_production()
        assert "JWT_SECRET_KEY" in str(exc.value)

    def test_production_safe_config_passes(self):
        """TC-ENV-007: 生产环境安全配置 → 校验通过"""
        s = Settings(
            environment="production",
            payment_mock_mode=False,
            alipay_sandbox=False,
            debug=False,
            jwt_secret_key="strong-jwt-secret-9f8a7b6c5d4e",
            secret_key="strong-app-secret-1a2b3c4d",
            api_key_encryption_secret="strong-enc-secret-5e6f7a8b",
            database_url="postgresql://prod_user:prod_pwd@db:5432/api_platform",
            redis_url="redis://:prod_redis_pwd@redis:6379/0",
        )
        s.validate_for_production()  # 不应抛异常
        assert s.collect_production_warnings() == []

    def test_default_config_is_not_production(self):
        """TC-ENV-008: 仓库默认配置不应被判定为生产环境（避免误拦截本地开发）"""
        assert global_settings.is_production is False


# ==================== 2. 环境过滤解析 ====================

class TestEnvironmentResolver:
    """resolve_environment 行为"""

    def test_none_falls_back_to_current_environment(self):
        """TC-ENV-009: 不传环境 → 使用当前环境"""
        assert resolve_environment(None) == current_environment()

    def test_blank_falls_back_to_current_environment(self):
        """TC-ENV-010: 空字符串 → 使用当前环境"""
        assert resolve_environment("") == current_environment()
        assert resolve_environment("   ") == current_environment()

    def test_all_means_no_filter(self):
        """TC-ENV-011: all 通配 → 不过滤（可查历史）"""
        assert resolve_environment("all") == ENVIRONMENT_ALL
        assert resolve_environment("ALL") == ENVIRONMENT_ALL
        assert resolve_environment(" All ") == ENVIRONMENT_ALL

    @pytest.mark.parametrize("env", VALID_ENVIRONMENTS)
    def test_valid_value_passthrough(self, env):
        """TC-ENV-012: 合法具体值原样返回（大小写不敏感）"""
        assert resolve_environment(env) == env
        assert resolve_environment(env.upper()) == env

    def test_invalid_value_degrades_to_current(self):
        """TC-ENV-013: 非法值降级为当前环境（不抛异常、不越权）"""
        assert resolve_environment("hacker") == current_environment()
        assert resolve_environment("simulation_x") == current_environment()

    def test_current_environment_matches_settings(self):
        """TC-ENV-014: current_environment 与 settings.billing_environment 一致"""
        assert current_environment() == global_settings.billing_environment


# ==================== 3. 环境过滤条件 ====================

class TestEnvMatch:
    """env_match 生成 SQLAlchemy 条件"""

    def test_all_returns_true_condition(self):
        """TC-ENV-015: all → 恒真条件（不过滤）"""
        from src.models.billing import Bill

        cond = env_match(Bill.environment, ENVIRONMENT_ALL)
        assert str(cond) == str(true())

    @pytest.mark.parametrize("env", VALID_ENVIRONMENTS)
    def test_concrete_value_builds_equality(self, env):
        """TC-ENV-016: 具体环境 → 生成等值条件"""
        from src.models.billing import Bill

        cond = env_match(Bill.environment, env)
        assert "environment" in str(cond)
        assert getattr(cond.right, "value", None) == env


# ==================== 4. 支付回调门控（集成） ====================

CALLBACK_URL = "/api/v1/payments/callback"
CALLBACK_BODY = {
    "payment_no": "PAY_TESTSAFE_0001",
    "transaction_id": "MOCK_TEST_0001",
    "status": "success",
    "payer_info": {"mock": True},
}


class TestPaymentCallbackGuard:
    """模拟支付回调门控（需要数据库连接）"""

    @pytest.mark.asyncio
    async def test_production_disables_generic_callback(self, client, monkeypatch):
        """TC-PAY-GUARD-001: 生产环境通用回调接口直接下线（404）"""
        monkeypatch.setattr(global_settings, "environment", "production", raising=False)

        resp = await client.post(CALLBACK_URL, json=CALLBACK_BODY)

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_mock_mode_requires_auth_or_internal_token(self, client, monkeypatch):
        """TC-PAY-GUARD-002: 非生产环境匿名调用 → 401"""
        monkeypatch.setattr(global_settings, "environment", "development", raising=False)
        monkeypatch.setattr(global_settings, "payment_mock_mode", True, raising=False)
        monkeypatch.setattr(global_settings, "internal_api_token", "", raising=False)

        resp = await client.post(CALLBACK_URL, json=CALLBACK_BODY)

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_mock_mode_wrong_internal_token_rejected(self, client, monkeypatch):
        """TC-PAY-GUARD-003: 内部令牌错误 → 401"""
        monkeypatch.setattr(global_settings, "environment", "development", raising=False)
        monkeypatch.setattr(global_settings, "payment_mock_mode", True, raising=False)
        monkeypatch.setattr(global_settings, "internal_api_token", "secret-token", raising=False)

        resp = await client.post(
            CALLBACK_URL,
            json=CALLBACK_BODY,
            headers={"X-Internal-Token": "wrong-token"},
        )

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_mock_mode_correct_internal_token_passes_gate(self, client, monkeypatch):
        """TC-PAY-GUARD-004: 内部令牌正确 → 通过门控（订单不存在也返回业务响应，非 401/403）"""
        monkeypatch.setattr(global_settings, "environment", "development", raising=False)
        monkeypatch.setattr(global_settings, "payment_mock_mode", True, raising=False)
        monkeypatch.setattr(global_settings, "internal_api_token", "secret-token", raising=False)

        resp = await client.post(
            CALLBACK_URL,
            json=CALLBACK_BODY,
            headers={"X-Internal-Token": "secret-token"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        # 订单不存在时应返回明确的业务提示，而不是抛 500
        assert body["data"]["success"] is False
        assert "订单不存在" in body["data"]["message"]


# ==================== 5. 账单环境落库验证（数据库记录级）====================

class TestBillingEnvironmentPersistence:
    """
    验证账单 environment **真正写入数据库**，且与 settings.billing_environment 一致。

    对应改造：billing_environment 与 payment_mock_mode 解耦
              —— "是否属于生产数据"由 ENVIRONMENT 决定。

    依赖数据库（PostgreSQL，使用 conftest 的 db_session / test_user）。
    """

    @pytest.mark.asyncio
    async def test_add_balance_persists_current_environment(self, db_session, test_user):
        """TC-ENV-017: 充值落库账单的 environment == billing_environment（默认取值）"""
        from sqlalchemy import select

        from src.models.billing import Bill
        from src.services.account_service import AccountService

        service = AccountService(db_session)
        await service.add_balance(
            user_id=str(test_user.id),
            amount=100.0,
            source_type="recharge",
            description="TC-ENV-017 环境落库验证",
        )
        await db_session.commit()

        # 从数据库重新读取，确认真正落库（而不是只看内存对象）
        rows = (
            await db_session.execute(select(Bill).where(Bill.user_id == test_user.id))
        ).scalars().all()
        assert len(rows) == 1

        persisted = rows[0]
        assert persisted.environment == global_settings.billing_environment
        # 测试运行环境为 development → 必须归 simulation
        assert persisted.environment == "simulation"

    @pytest.mark.asyncio
    async def test_explicit_environment_is_respected(self, db_session, test_user):
        """TC-ENV-018: 显式传入 environment 时以显式值为准（补录/迁移场景）"""
        from sqlalchemy import select

        from src.models.billing import Bill
        from src.services.account_service import AccountService

        service = AccountService(db_session)
        await service.add_balance(
            user_id=str(test_user.id),
            amount=50.0,
            source_type="recharge",
            description="TC-ENV-018 显式环境",
            environment="production",
        )
        await db_session.commit()

        rows = (
            await db_session.execute(select(Bill).where(Bill.user_id == test_user.id))
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].environment == "production"

    @pytest.mark.asyncio
    async def test_persisted_bill_matches_env_match_filter(self, db_session, test_user):
        """TC-ENV-019: 落库账单可被「当前环境」命中，且不被另一环境命中，all 可命中"""
        from sqlalchemy import select

        from src.models.billing import Bill
        from src.services.account_service import AccountService

        service = AccountService(db_session)
        await service.add_balance(
            user_id=str(test_user.id),
            amount=20.0,
            source_type="recharge",
            description="TC-ENV-019 环境过滤",
        )
        await db_session.commit()

        current = current_environment()
        other = "production" if current == "simulation" else "simulation"

        async def _count(env: str) -> int:
            return len(
                (
                    await db_session.execute(
                        select(Bill).where(
                            Bill.user_id == test_user.id,
                            env_match(Bill.environment, env),
                        )
                    )
                ).scalars().all()
            )

        # 当前环境命中
        assert await _count(current) == 1
        # 另一环境不命中（数据隔离）
        assert await _count(other) == 0
        # all 通配命中（排查/对账）
        assert await _count(ENVIRONMENT_ALL) == 1


# ==================== 6. 账单环境默认值与写入守卫（防漏传） ====================

class TestBillingEnvironmentDefaultAndGuard:
    """
    验证「默认值跟随环境」(L1) 与「写入守卫」(L3)。

    这两层共同解决：生产环境漏传 environment → 静默写成 simulation → 对账漏账。
    """

    def test_model_default_follows_environment(self):
        """TC-ENV-020: 模型默认值改为「跟随运行环境的可调用对象」（不再是硬编码 simulation）"""
        from src.models.billing import Bill, MonthlyBill, _current_billing_environment

        # 1) 列默认值必须是可调用对象（而非固定字符串 "simulation"）
        #    注意：SQLAlchemy 会把无参 callable 包装为接受 ExecutionContext 的形式，
        #          因此这里只断言"是可调用对象"，取值逻辑由第 2 条与落库用例 (TC-ENV-022) 验证。
        for column in (Bill.environment, MonthlyBill.environment):
            assert column.default is not None, "environment 必须声明默认值"
            assert callable(column.default.arg), "environment 默认值必须是可调用对象（跟随环境）"

        # 2) 取值逻辑跟随 settings.billing_environment
        assert _current_billing_environment() == global_settings.billing_environment

    def test_default_is_production_in_production_env(self, monkeypatch):
        """TC-ENV-021: 生产环境下默认值为 production（即便漏传也不会漏账）"""
        from src.models.billing import _current_billing_environment

        monkeypatch.setattr(global_settings, "environment", "production", raising=False)
        assert _current_billing_environment() == "production"

    @pytest.mark.asyncio
    async def test_missing_environment_persists_current_environment(self, db_session, test_user):
        """TC-ENV-022: 落库验证 —— 未显式传 environment 时按当前环境写入"""
        from src.models.billing import Bill

        bill = Bill(
            user_id=test_user.id,
            bill_no="TEST_DEFAULT_ENV_0001",
            bill_type="recharge",
            amount="1.0",
            balance_before="0",
            balance_after="1.0",
        )
        db_session.add(bill)
        await db_session.commit()
        await db_session.refresh(bill)

        assert bill.environment == global_settings.billing_environment
        # 测试运行于 development → 必须是 simulation
        assert bill.environment == "simulation"

    def test_guard_logs_error_for_production_simulation(self, monkeypatch):
        """TC-ENV-023: 守卫 —— 生产环境写入 simulation 账单会记录 ERROR（明显提示）"""
        from unittest.mock import patch

        from src.models import billing as billing_module
        from src.models.billing import Bill

        monkeypatch.setattr(global_settings, "environment", "production", raising=False)
        target = Bill(environment="simulation", bill_no="BILL_GUARD_0001", amount="1.0")

        with patch.object(billing_module.logger, "error") as mock_error:
            billing_module._guard_environment_on_insert(target, "Bill")

        assert mock_error.called
        assert "账单环境异常" in str(mock_error.call_args)

    def test_guard_fills_blank_environment(self):
        """TC-ENV-024: 守卫 —— environment 为空时按当前环境补全"""
        from src.models import billing as billing_module
        from src.models.billing import Bill

        target = Bill(environment=None)
        billing_module._guard_environment_on_insert(target, "Bill")

        assert target.environment == global_settings.billing_environment

    @pytest.mark.asyncio
    async def test_environment_response_headers(self, client):
        """TC-ENV-025: 所有响应携带 X-Environment / X-Billing-Environment"""
        resp = await client.get("/health")

        assert resp.headers.get("X-Environment") == global_settings.environment
        assert resp.headers.get("X-Billing-Environment") == global_settings.billing_environment

    @pytest.mark.asyncio
    async def test_health_exposes_environment_for_frontend(self, client):
        """TC-ENV-026: /health 暴露环境标识（供前端环境徽标使用）"""
        resp = await client.get("/health")
        body = resp.json()

        assert body["environment"] == global_settings.environment
        assert body["billing_environment"] == global_settings.billing_environment
        assert body["is_production"] == global_settings.is_production


# ==================== 6.1 对账环境隔离（数据库记录级） ====================


class TestReconciliationEnvironmentIsolation:
    """
    验证对账模块的「本地交易查询」只统计当前环境的账单。

    对应改造：admin_reconciliation / reconciliation_scheduler 的 Bill 查询
    统一追加 ``env_match(Bill.environment, current_environment())`` ——
    生产对账不混入 simulation 账单（反之亦然），避免历史混合数据污染对账口径。
    """

    @pytest.mark.asyncio
    async def test_reconciliation_conditions_filter_other_environment(
        self, db_session, test_user
    ):
        """TC-ENV-027: 同窗口同渠道两笔账单（当前环境 + 另一环境），对账条件只命中当前环境"""
        import uuid as _uuid
        from datetime import timedelta

        from sqlalchemy import and_, select

        from src.models.billing import Bill
        from src.utils.time_range import cst_day_range_utc_from_date, cst_now

        today = cst_now().date()
        day_start, day_end = cst_day_range_utc_from_date(today)

        current = current_environment()
        other = "production" if current == "simulation" else "simulation"

        # 模拟对账场景的"本地充值"：同渠道、同状态、同窗口，仅 environment 不同
        for env in (current, other):
            db_session.add(
                Bill(
                    user_id=test_user.id,
                    bill_no=f"TEST_RECON_{env}_{_uuid.uuid4().hex[:8]}",
                    bill_type="recharge",
                    amount="100.0",
                    balance_before="0",
                    balance_after="100.0",
                    payment_method="alipay",
                    status="completed",
                    environment=env,
                    created_at=day_start + timedelta(hours=5),
                )
            )
        await db_session.commit()

        # 与 admin_reconciliation / reconciliation_scheduler 相同的对账查询条件
        conditions = [
            Bill.created_at >= day_start,
            Bill.created_at < day_end,
            Bill.bill_type == "recharge",
            Bill.payment_method == "alipay",
            Bill.status == "completed",
            env_match(Bill.environment, current),
        ]
        rows = (
            await db_session.execute(select(Bill).where(and_(*conditions)))
        ).scalars().all()

        assert len(rows) == 1
        assert rows[0].environment == current

    def test_generate_bill_no_format(self):
        """TC-ENV-028: generate_bill_no 存活回归（死代码清理后唯一保留的 billing_service 出口）"""
        from src.services.billing_service import generate_bill_no

        bill_no = generate_bill_no()

        assert bill_no.startswith("BILL")
        assert len(bill_no) == 4 + 14 + 6  # 前缀 + UTC 时间戳 + 6 位随机
        assert bill_no[4:18].isdigit()     # 时间戳段全数字
        assert bill_no[18:].isdigit()      # 随机段全数字


# ==================== 7. 分库护栏（环境 ↔ 数据库 一致性） ====================

class TestDatabaseSeparationGuard:
    """
    验证「分库护栏」：不同环境必须使用独立数据库，且禁止交叉连接。

    最重要的场景：**非生产环境误连生产库** → 拒绝启动（防误操作生产数据）。
    """

    def test_non_production_rejects_production_database(self):
        """TC-DB-001: 非生产环境指向生产库 → 拒绝启动"""
        s = Settings(
            environment="development",
            database_url="postgresql://u:p@h:5432/api_platform_prod",
        )
        assert s.database_name == "api_platform_prod"

        issues = s.collect_database_separation_issues()
        assert issues and "生产库" in issues[0]

        with pytest.raises(RuntimeError) as exc:
            s.validate_database_separation()
        assert "拒绝启动" in str(exc.value)

    def test_production_rejects_dev_database(self):
        """TC-DB-002: 生产环境指向开发库 → 判定为问题项"""
        s = Settings(
            environment="production",
            database_url="postgresql://u:p@h:5432/api_platform_dev",
        )
        issues = s.collect_database_separation_issues()
        assert issues and "非生产库" in issues[0]

    def test_production_rejects_test_database(self):
        """TC-DB-003: 生产环境指向测试库 → 判定为问题项"""
        s = Settings(
            environment="production",
            database_url="postgresql://u:p@h:5432/api_platform_test",
        )
        assert s.collect_database_separation_issues()

    def test_non_production_allows_dev_database(self):
        """TC-DB-004: 非生产环境指向开发库 → 通过"""
        s = Settings(
            environment="development",
            database_url="postgresql://u:p@h:5432/api_platform_dev",
        )
        assert s.collect_database_separation_issues() == []
        s.validate_database_separation()  # 不应抛异常

    def test_explicit_override_allows_production_database(self):
        """TC-DB-005: 显式 ALLOW_PRODUCTION_DATABASE=true → 放行"""
        s = Settings(
            environment="development",
            allow_production_database=True,
            database_url="postgresql://u:p@h:5432/api_platform_prod",
        )
        s.validate_database_separation()  # 不应抛异常

    def test_database_name_extraction_with_query_params(self):
        """TC-DB-006: 库名提取（含连接串 query 参数）"""
        s = Settings(
            database_url="postgresql+asyncpg://u:p@h:5432/api_platform_dev?sslmode=require"
        )
        assert s.database_name == "api_platform_dev"

    def test_current_environment_database_passes_guard(self):
        """TC-DB-007: 当前实际配置（开发环境 + dev 库）通过护栏"""
        assert global_settings.collect_database_separation_issues() == []
        global_settings.validate_database_separation()  # 不应抛异常
