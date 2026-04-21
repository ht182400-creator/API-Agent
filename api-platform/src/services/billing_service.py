"""
Billing Service - 计费服务
完整的API实现逻辑
"""

import uuid
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from src.models.billing import Account, Bill, Quota
from src.models.user import User
from src.models.api_key import APIKey
from src.core.exceptions import (
    ValidationError,
    QuotaExceededError,
    NotFoundError,
)
from src.config.logging_config import get_logger

# 模块日志记录器
logger = get_logger("billing")


def generate_bill_no() -> str:
    """生成账单号"""
    import random
    import string
    prefix = "BILL"
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.digits, k=6))
    return f"{prefix}{timestamp}{random_str}"


class BillingService:
    """计费服务 - 核心业务逻辑"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_account(
        self,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
    ) -> Account:
        """
        获取账户信息

        Args:
            user_id: 用户ID
            api_key_id: API Key ID (保留参数，暂未使用)

        Returns:
            账户对象
        """
        if not user_id and not api_key_id:
            raise ValidationError("必须提供user_id或api_key_id")

        query = select(Account)
        if user_id:
            query = query.where(Account.user_id == uuid.UUID(user_id))

        result = await self.db.execute(query)
        account = result.scalar_one_or_none()

        if not account:
            # 创建默认账户
            if user_id:
                account = await self._create_default_account(user_id)
            else:
                raise NotFoundError("账户不存在")

        return account

    async def _create_default_account(self, user_id: str) -> Account:
        """创建默认账户"""
        account = Account(
            user_id=uuid.UUID(user_id),
            account_type="balance",
            balance="0.00",
            frozen_balance="0.00",
            total_recharge="0.00",
            total_consume="0.00",
        )
        self.db.add(account)
        await self.db.flush()
        await self.db.refresh(account)
        return account

    async def recharge(
        self,
        user_id: str,
        amount: float,
        payment_method: str = "manual",
        payment_id: Optional[str] = None,
        description: str = "",
    ) -> Tuple[Account, Bill]:
        """
        账户充值

        Args:
            user_id: 用户ID
            amount: 充值金额
            payment_method: 支付方式
            payment_id: 支付流水号
            description: 描述

        Returns:
            (更新后的账户, 账单记录)
        """
        if amount <= 0:
            raise ValidationError("充值金额必须大于0")

        account = await self.get_account(user_id=user_id)

        # 记录充值前的余额
        balance_before = account.balance

        # 更新余额
        new_balance = Decimal(str(account.balance)) + Decimal(str(amount))
        account.balance = str(new_balance)
        account.total_recharge = str(Decimal(str(account.total_recharge)) + Decimal(str(amount)))

        # 构建描述
        desc = description or f"账户充值: {amount}元"
        if payment_id:
            desc = f"{desc} (支付单号: {payment_id})"

        # 创建账单
        bill = Bill(
            user_id=uuid.UUID(user_id),
            bill_no=generate_bill_no(),
            bill_type="recharge",
            amount=str(amount),
            balance_before=str(balance_before),
            balance_after=str(new_balance),
            source_type="manual",
            source_id=payment_id,
            description=desc,
            status="completed",
            payment_method=payment_method,
        )
        self.db.add(bill)
        await self.db.flush()
        await self.db.refresh(account)
        await self.db.refresh(bill)

        return account, bill

    async def create_consumption(
        self,
        user_id: str,
        api_key_id: str,
        repo_id: str,
        amount: float,
        description: str = "",
        metadata: Optional[Dict] = None,
    ) -> Tuple[Account, Bill]:
        """
        创建消费记录

        Args:
            user_id: 用户ID
            api_key_id: API Key ID (存入source_id)
            repo_id: 仓库ID (存入description)
            amount: 消费金额
            description: 描述
            metadata: 元数据 (存入description)

        Returns:
            (更新后的账户, 账单记录)
        """
        account = await self.get_account(user_id=user_id)

        # 检查余额
        if Decimal(str(account.balance)) < Decimal(str(amount)):
            raise QuotaExceededError("余额不足")

        # 记录消费前的余额
        balance_before = account.balance

        # 扣减余额
        new_balance = Decimal(str(account.balance)) - Decimal(str(amount))
        account.balance = str(new_balance)
        account.total_consume = str(Decimal(str(account.total_consume)) + Decimal(str(amount)))

        # 构建描述
        desc = description or f"API调用消费"
        if repo_id:
            desc = f"{desc} - 仓库: {repo_id[:8]}..."
        if metadata:
            desc = f"{desc} ({metadata})"

        # 创建账单 - api_key_id存入source_id
        bill = Bill(
            user_id=uuid.UUID(user_id),
            bill_no=generate_bill_no(),
            bill_type="consume",
            amount=str(-abs(amount)),
            balance_before=str(balance_before),
            balance_after=str(new_balance),
            source_type="api_call",
            source_id=api_key_id,
            description=desc,
            status="completed",
        )
        self.db.add(bill)
        await self.db.flush()
        await self.db.refresh(account)
        await self.db.refresh(bill)

        return account, bill

    async def freeze_balance(
        self,
        user_id: str,
        amount: float,
        reason: str = "",
    ) -> Account:
        """
        冻结余额（用于套餐预购等）

        Args:
            user_id: 用户ID
            amount: 冻结金额
            reason: 冻结原因

        Returns:
            更新后的账户
        """
        account = await self.get_account(user_id=user_id)

        if Decimal(str(account.balance)) < Decimal(str(amount)):
            raise ValidationError("余额不足")

        # 记录冻结前的余额
        balance_before = account.balance

        # 转移余额到冻结
        new_balance = Decimal(str(account.balance)) - Decimal(str(amount))
        account.balance = str(new_balance)
        account.frozen_balance = str(Decimal(str(account.frozen_balance)) + Decimal(str(amount)))

        # 记录账单
        bill = Bill(
            user_id=uuid.UUID(user_id),
            bill_no=generate_bill_no(),
            bill_type="freeze",
            amount=str(-abs(amount)),
            balance_before=str(balance_before),
            balance_after=str(new_balance),
            source_type="freeze",
            description=reason or f"冻结余额: {amount}元",
            status="completed",
        )
        self.db.add(bill)
        await self.db.flush()
        await self.db.refresh(account)

        return account

    async def unfreeze_balance(
        self,
        user_id: str,
        amount: float,
        reason: str = "",
    ) -> Account:
        """
        解冻余额

        Args:
            user_id: 用户ID
            amount: 解冻金额
            reason: 解冻原因

        Returns:
            更新后的账户
        """
        account = await self.get_account(user_id=user_id)

        if Decimal(str(account.frozen_balance)) < Decimal(str(amount)):
            raise ValidationError("冻结余额不足")

        # 记录解冻前的余额
        balance_before = account.balance

        # 转移冻结到余额
        account.frozen_balance = str(Decimal(str(account.frozen_balance)) - Decimal(str(amount)))
        new_balance = Decimal(str(account.balance)) + Decimal(str(amount))
        account.balance = str(new_balance)

        # 记录账单
        bill = Bill(
            user_id=uuid.UUID(user_id),
            bill_no=generate_bill_no(),
            bill_type="unfreeze",
            amount=str(amount),
            balance_before=str(balance_before),
            balance_after=str(new_balance),
            source_type="unfreeze",
            description=reason or f"解冻余额: {amount}元",
            status="completed",
        )
        self.db.add(bill)
        await self.db.flush()
        await self.db.refresh(account)

        return account

    async def refund(
        self,
        user_id: str,
        amount: float,
        original_bill_id: str,
        reason: str = "",
    ) -> Tuple[Account, Bill]:
        """
        退款

        Args:
            user_id: 用户ID
            amount: 退款金额
            original_bill_id: 原账单ID (存入source_id)
            reason: 退款原因

        Returns:
            (更新后的账户, 退款账单)
        """
        account = await self.get_account(user_id=user_id)

        # 记录退款前的余额
        balance_before = account.balance

        # 退还余额
        new_balance = Decimal(str(account.balance)) + Decimal(str(amount))
        account.balance = str(new_balance)
        account.total_recharge = str(Decimal(str(account.total_recharge)) + Decimal(str(amount)))

        # 构建描述
        desc = reason or f"退款: {amount}元"
        if original_bill_id:
            desc = f"{desc} (原账单: {original_bill_id[:8]}...)"

        # 创建退款账单 - original_bill_id存入source_id
        bill = Bill(
            user_id=uuid.UUID(user_id),
            bill_no=generate_bill_no(),
            bill_type="refund",
            amount=str(amount),
            balance_before=str(balance_before),
            balance_after=str(new_balance),
            source_type="refund",
            source_id=original_bill_id,
            description=desc,
            status="completed",
        )
        self.db.add(bill)
        await self.db.flush()
        await self.db.refresh(account)
        await self.db.refresh(bill)

        return account, bill

    async def get_bills(
        self,
        user_id: str,
        bill_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Bill], int]:
        """
        获取账单列表

        Args:
            user_id: 用户ID
            bill_type: 账单类型
            start_date: 开始日期
            end_date: 结束日期
            page: 页码
            page_size: 每页数量

        Returns:
            (账单列表, 总数)
        """
        # 直接使用 user_id 查询账单
        query = select(Bill).where(Bill.user_id == uuid.UUID(user_id))
        count_query = select(func.count(Bill.id)).where(Bill.user_id == uuid.UUID(user_id))

        # 筛选
        filters = []
        if bill_type:
            filters.append(Bill.bill_type == bill_type)
        if start_date:
            filters.append(Bill.created_at >= start_date)
        if end_date:
            filters.append(Bill.created_at <= end_date)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # 总数
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        query = query.order_by(Bill.created_at.desc())

        result = await self.db.execute(query)
        bills = result.scalars().all()

        return list(bills), total

    async def get_balance_history(
        self,
        user_id: str,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        获取余额历史（每日快照）

        Args:
            user_id: 用户ID
            days: 天数

        Returns:
            余额历史列表
        """
        account = await self.get_account(user_id=user_id)
        
        start_date = datetime.utcnow() - timedelta(days=days)

        # 按日期分组统计
        query = select(
            func.date(Bill.created_at).label("date"),
            func.sum(func.cast(Bill.amount, __import__('sqlalchemy').Numeric)).label("daily_change"),
        ).where(
            and_(
                Bill.user_id == uuid.UUID(user_id),
                Bill.created_at >= start_date,
            )
        ).group_by(
            func.date(Bill.created_at)
        ).order_by(
            func.date(Bill.created_at)
        )

        result = await self.db.execute(query)
        rows = result.all()

        # 计算累计余额
        history = []
        current_balance = float(account.balance)
        
        for row in reversed(rows):
            history.append({
                "date": row.date,
                "daily_change": float(row.daily_change) if row.daily_change else 0,
                "balance": current_balance,
            })
            current_balance -= float(row.daily_change) if row.daily_change else 0

        return list(reversed(history))

    async def get_monthly_summary(
        self,
        user_id: str,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        获取月度账单汇总

        Args:
            user_id: 用户ID
            year: 年份
            month: 月份

        Returns:
            月度汇总信息
        """
        if not year:
            year = datetime.utcnow().year
        if not month:
            month = datetime.utcnow().month

        account = await self.get_account(user_id=user_id)

        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        # 充值汇总 (recharge和refund都是正向金额)
        recharge_query = select(
            func.sum(func.cast(Bill.amount, __import__('sqlalchemy').Numeric)).label("total")
        ).where(
            and_(
                Bill.user_id == uuid.UUID(user_id),
                Bill.bill_type.in_(["recharge", "refund"]),
                Bill.created_at >= start_date,
                Bill.created_at < end_date,
            )
        )
        recharge_result = await self.db.execute(recharge_query)
        total_recharge = recharge_result.scalar() or Decimal("0")

        # 消费汇总 (consumption是负数，需要取绝对值)
        consumption_query = select(
            func.sum(func.abs(func.cast(Bill.amount, __import__('sqlalchemy').Numeric))).label("total"),
            func.count(Bill.id).label("count"),
        ).where(
            and_(
                Bill.user_id == uuid.UUID(user_id),
                Bill.bill_type == "consumption",
                Bill.created_at >= start_date,
                Bill.created_at < end_date,
            )
        )
        consumption_result = await self.db.execute(consumption_query)
        consumption_row = consumption_result.one()
        total_consumption = consumption_row.total or Decimal("0")
        consumption_count = consumption_row.count

        # 按source_id统计 (如按API Key)
        source_query = select(
            Bill.source_id,
            func.sum(func.abs(func.cast(Bill.amount, __import__('sqlalchemy').Numeric))).label("total"),
            func.count(Bill.id).label("count"),
        ).where(
            and_(
                Bill.user_id == uuid.UUID(user_id),
                Bill.bill_type == "consumption",
                Bill.source_id.isnot(None),
                Bill.created_at >= start_date,
                Bill.created_at < end_date,
            )
        ).group_by(Bill.source_id)

        source_result = await self.db.execute(source_query)
        source_stats = []
        for row in source_result:
            source_stats.append({
                "source_id": str(row.source_id) if row.source_id else None,
                "total": float(row.total),
                "count": row.count,
            })

        return {
            "year": year,
            "month": month,
            "total_recharge": float(total_recharge),
            "total_consumption": float(total_consumption),
            "consumption_count": consumption_count,
            "net_change": float(total_recharge) - float(total_consumption),
            "by_source": source_stats,
        }

    async def transfer_to_owner(
        self,
        repo_id: str,
        user_id: str,
        amount: float,
        description: str = "",
    ) -> Bill:
        """
        向仓库所有者转账（收益结算）

        Args:
            repo_id: 仓库ID (存入source_id)
            user_id: 目标用户ID
            amount: 金额
            description: 描述

        Returns:
            账单记录
        """
        account = await self.get_account(user_id=user_id)

        # 记录结算前的余额
        balance_before = account.balance

        # 减少冻结余额（或增加可用余额）
        if Decimal(str(account.frozen_balance)) >= Decimal(str(amount)):
            account.frozen_balance = str(Decimal(str(account.frozen_balance)) - Decimal(str(amount)))
        else:
            new_balance = Decimal(str(account.balance)) + Decimal(str(amount))
            account.balance = str(new_balance)

        # 记录账单
        bill = Bill(
            user_id=uuid.UUID(user_id),
            bill_no=generate_bill_no(),
            bill_type="settlement",
            amount=str(amount),
            balance_before=str(balance_before),
            balance_after=account.balance,
            source_type="settlement",
            source_id=repo_id,
            description=description or f"收益结算: {amount}元",
            status="completed",
        )
        self.db.add(bill)
        await self.db.flush()
        await self.db.refresh(bill)

        return bill
