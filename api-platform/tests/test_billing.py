"""
Billing Service Tests - 计费服务测试
"""

import pytest
import uuid
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.billing_service import BillingService
from src.models.billing import Account, Bill
from src.core.exceptions import ValidationError, QuotaExceededError


class TestBillingService:
    """计费服务测试类"""

    @pytest.fixture
    async def billing_service(self, db_session: AsyncSession) -> BillingService:
        """创建计费服务实例"""
        return BillingService(db_session)

    @pytest.fixture
    async def user_with_account(self, db_session: AsyncSession) -> tuple:
        """创建测试用户和关联账户"""
        from src.models.user import User
        from src.core.security import hash_password

        # 创建用户
        user = User(
            email=f"billing_{uuid.uuid4().hex[:8]}@test.com",
            password_hash=hash_password("testpassword123"),
            user_type="developer",
            user_status="active",
        )
        db_session.add(user)
        await db_session.flush()

        # 创建关联账户
        account = Account(
            user_id=user.id,
            account_type="balance",
            balance="100.00",  # 初始余额100元
            frozen_balance="0.00",
            total_recharge="100.00",
            total_consume="0.00",
        )
        db_session.add(account)
        await db_session.flush()

        return user, account

    async def test_get_account(self, db_session: AsyncSession, user_with_account: tuple):
        """测试获取账户"""
        user, expected_account = user_with_account
        service = BillingService(db_session)

        account = await service.get_account(user_id=str(user.id))

        assert account is not None
        assert str(account.user_id) == str(user.id)
        assert account.account_type == "balance"
        assert float(account.balance) == 100.00

    async def test_get_account_auto_create(self, db_session: AsyncSession, test_user):
        """测试自动创建账户"""
        service = BillingService(db_session)

        # 不存在则自动创建
        account = await service.get_account(user_id=str(test_user.id))

        assert account is not None
        assert str(account.user_id) == str(test_user.id)
        assert float(account.balance) == 0.00

    async def test_recharge(self, db_session: AsyncSession, user_with_account: tuple):
        """测试充值"""
        user, account = user_with_account
        service = BillingService(db_session)

        updated_account, bill = await service.recharge(
            user_id=str(user.id),
            amount=50.00,
            payment_method="alipay",
            payment_id="PAY123456",
        )

        assert float(updated_account.balance) == 150.00
        assert float(updated_account.total_recharge) == 150.00
        assert bill is not None
        assert bill.bill_type == "recharge"
        assert float(bill.amount) == 50.00

    async def test_recharge_negative_amount(self, db_session: AsyncSession, user_with_account: tuple):
        """测试负数充值被拒绝"""
        user, _ = user_with_account
        service = BillingService(db_session)

        with pytest.raises(ValidationError):
            await service.recharge(user_id=str(user.id), amount=-10.00)

    async def test_create_consumption(self, db_session: AsyncSession, user_with_account: tuple):
        """测试创建消费记录"""
        user, account = user_with_account
        service = BillingService(db_session)

        api_key_id = str(uuid.uuid4())

        updated_account, bill = await service.create_consumption(
            user_id=str(user.id),
            api_key_id=api_key_id,
            repo_id=str(uuid.uuid4()),
            amount=30.00,
            description="API调用费用",
        )

        assert float(updated_account.balance) == 70.00
        assert float(updated_account.total_consume) == 30.00
        assert bill is not None
        assert bill.bill_type == "consumption"
        assert float(bill.amount) == -30.00
        # api_key_id存入source_id
        assert str(bill.source_id) == api_key_id

    async def test_insufficient_balance(self, db_session: AsyncSession, user_with_account: tuple):
        """测试余额不足"""
        user, account = user_with_account
        service = BillingService(db_session)

        with pytest.raises(QuotaExceededError):
            await service.create_consumption(
                user_id=str(user.id),
                api_key_id=str(uuid.uuid4()),
                repo_id=str(uuid.uuid4()),
                amount=200.00,  # 超过余额
            )

    async def test_freeze_balance(self, db_session: AsyncSession, user_with_account: tuple):
        """测试冻结余额"""
        user, account = user_with_account
        service = BillingService(db_session)

        updated_account = await service.freeze_balance(
            user_id=str(user.id),
            amount=50.00,
            reason="预购套餐",
        )

        assert float(updated_account.balance) == 50.00
        assert float(updated_account.frozen_balance) == 50.00

    async def test_unfreeze_balance(self, db_session: AsyncSession, user_with_account: tuple):
        """测试解冻余额"""
        user, account = user_with_account
        service = BillingService(db_session)

        # 先冻结
        await service.freeze_balance(user_id=str(user.id), amount=50.00)

        # 再解冻
        updated_account = await service.unfreeze_balance(
            user_id=str(user.id),
            amount=30.00,
        )

        assert float(updated_account.balance) == 80.00
        assert float(updated_account.frozen_balance) == 20.00

    async def test_refund(self, db_session: AsyncSession, user_with_account: tuple):
        """测试退款"""
        user, account = user_with_account
        service = BillingService(db_session)

        original_bill_id = str(uuid.uuid4())

        updated_account, bill = await service.refund(
            user_id=str(user.id),
            amount=25.00,
            original_bill_id=original_bill_id,
            reason="重复扣费退款",
        )

        assert float(updated_account.balance) == 125.00
        assert float(updated_account.total_recharge) == 125.00
        assert bill is not None
        assert bill.bill_type == "refund"
        assert float(bill.amount) == 25.00
        assert str(bill.source_id) == original_bill_id

    async def test_get_bills(self, db_session: AsyncSession, user_with_account: tuple):
        """测试获取账单列表"""
        user, account = user_with_account
        service = BillingService(db_session)

        # 创建几条账单
        await service.recharge(user_id=str(user.id), amount=50.00)
        await service.recharge(user_id=str(user.id), amount=30.00)

        bills, total = await service.get_bills(user_id=str(user.id))

        assert total >= 2
        assert len(bills) >= 2

    async def test_get_monthly_summary(self, db_session: AsyncSession, user_with_account: tuple):
        """测试月度汇总"""
        user, account = user_with_account
        service = BillingService(db_session)

        # 创建充值
        await service.recharge(user_id=str(user.id), amount=100.00)

        summary = await service.get_monthly_summary(user_id=str(user.id))

        assert summary["total_recharge"] >= 100.00
        assert "consumption_count" in summary
        assert "net_change" in summary
