"""Account Service - 账户服务"""

import uuid
import json
import time
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from src.models.billing import Account, Bill
from src.core.exceptions import (
    ValidationError,
    NotFoundError,
    InsufficientBalanceError,
)


class AccountService:
    """账户服务 - 核心业务逻辑"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def generate_bill_no(self) -> str:
        """生成账单号"""
        timestamp = int(time.time())
        random_str = uuid.uuid4().hex[:6].upper()
        return f"BILL{timestamp}{random_str}"
    
    async def get_or_create_account(self, user_id: str) -> Account:
        """
        获取或创建用户账户
        
        【重要】此方法假设调用者会负责事务提交（commit）。
        使用数据库唯一约束保证并发场景下只会创建一个账户。
        如果唯一约束冲突（并发创建），会回滚并重新查询已创建的账户。
        
        Args:
            user_id: 用户ID
            
        Returns:
            账户对象
        """
        from src.config.logging_config import get_logger
        from sqlalchemy.exc import IntegrityError
        
        logger = get_logger("account")
        
        try:
            logger.info(f"[GetOrCreate] Looking for account: user_id={user_id}")
            result = await self.db.execute(
                select(Account).where(
                    and_(
                        Account.user_id == uuid.UUID(user_id),
                        Account.account_type == "balance"
                    )
                )
            )
            accounts = result.scalars().all()
            logger.info(f"[GetOrCreate] Found {len(accounts)} account(s) for user {user_id}")
            
            # 处理多记录情况（理论上在唯一约束下不会发生）
            if len(accounts) > 1:
                logger.warning(f"[GetOrCreate] Multiple accounts found for user {user_id}, using first one")
                account = accounts[0]
            elif len(accounts) == 0:
                logger.info(f"[GetOrCreate] No account found, creating new one for user {user_id}")
                account = None
            else:
                account = accounts[0]
            
            if not account:
                account = Account(
                    user_id=uuid.UUID(user_id),
                    account_type="balance",
                    balance="0",
                    frozen_balance="0",
                    total_recharge="0",
                    total_consume="0",
                )
                self.db.add(account)
                # 【修复】这里只 flush 不 commit，由调用者统一管理事务
                await self.db.flush()
                logger.info(f"[GetOrCreate] Account staged (not committed yet): user_id={user_id}")
            
            return account
        except IntegrityError as e:
            logger.error(f"[GetOrCreate] IntegrityError for user {user_id}: {e}")
            await self.db.rollback()
            # 唯一约束冲突：说明其他请求已经创建了账户
            logger.info(f"[GetOrCreate] Account already exists (concurrent creation), querying...")
            result = await self.db.execute(
                select(Account).where(
                    and_(
                        Account.user_id == uuid.UUID(user_id),
                        Account.account_type == "balance"
                    )
                )
            )
            account = result.scalars().first()
            if not account:
                raise RuntimeError(f"账户创建失败且无法查询到账户: {user_id}")
            logger.info(f"[GetOrCreate] Retrieved existing account: id={account.id}")
            return account
        except Exception as e:
            logger.error(f"[GetOrCreate] Error getting account for user {user_id}: {e}")
            raise
    
    async def get_balance(self, user_id: str) -> float:
        """
        获取账户余额
        
        Args:
            user_id: 用户ID
            
        Returns:
            账户余额
        """
        account = await self.get_or_create_account(user_id)
        return float(account.balance)
    
    async def add_balance(
        self,
        user_id: str,
        amount: float,
        source_type: str = "recharge",
        source_id: str = None,
        description: str = None,
        environment: str = None,
    ) -> Tuple[Account, Bill]:
        """
        增加账户余额
        
        【重要】此方法假设调用者会负责事务提交（commit）。
        主要目的是确保账户更新和账单创建在同一事务中。
        
        Args:
            user_id: 用户ID
            amount: 增加金额
            source_type: 来源类型 (recharge/bonus/refund)
            source_id: 来源ID
            description: 描述
            environment: 环境标志 (simulation/production)
            
        Returns:
            (更新后的账户, 账单记录)
        """
        from src.config.logging_config import get_logger
        logger = get_logger("account")
        
        logger.info(f"[AddBalance] Starting add_balance: user_id={user_id}, amount={amount}, source_type={source_type}")
        
        if amount <= 0:
            raise ValidationError("增加金额必须大于0")
        
        # 如果未指定环境，根据配置自动判断
        if environment is None:
            from src.config.settings import settings
            environment = "simulation" if settings.payment_mock_mode else "production"
        
        account = await self.get_or_create_account(user_id)
        logger.info(f"[AddBalance] Account obtained: id={account.id}, user_id={account.user_id}, current_balance={account.balance}")
        
        # 计算新余额
        old_balance = float(account.balance or "0")
        new_balance = old_balance + amount
        old_total_recharge = float(account.total_recharge or "0")
        new_total_recharge = old_total_recharge + amount if source_type == "recharge" else old_total_recharge
        
        logger.info(f"[AddBalance] Balance update: {old_balance} + {amount} = {new_balance}")
        
        # 更新账户余额
        account.balance = str(new_balance)
        if source_type == "recharge":
            account.total_recharge = str(new_total_recharge)
        
        logger.info(f"[AddBalance] Account object updated, balance={account.balance}, total_recharge={account.total_recharge}")
        
        # 创建账单记录
        bill = Bill(
            user_id=uuid.UUID(user_id),
            bill_no=self.generate_bill_no(),
            bill_type=source_type,
            amount=str(amount),
            balance_before=str(old_balance),
            balance_after=str(new_balance),
            source_type=source_type,
            source_id=source_id,
            description=description,
            status="completed",
            completed_at=datetime.utcnow(),
            environment=environment,
        )
        self.db.add(bill)
        
        # 【修复】确保 flush 在 commit 之前，并且只 flush 不 commit
        # 由调用者统一管理事务提交
        await self.db.flush()
        logger.info(f"[AddBalance] Flushed: balance={account.balance}, bill_no={bill.bill_no}")
        
        return account, bill
    
    async def deduct_balance(
        self,
        user_id: str,
        amount: float,
        source_type: str = "consume",
        source_id: str = None,
        description: str = None,
    ) -> Tuple[Account, Bill]:
        """
        扣除账户余额
        
        【重要】此方法假设调用者会负责事务提交（commit）。
        
        Args:
            user_id: 用户ID
            amount: 扣除金额
            source_type: 来源类型 (consume/refund/withdraw)
            source_id: 来源ID
            description: 描述
            
        Returns:
            (更新后的账户, 账单记录)
        """
        from src.config.logging_config import get_logger
        logger = get_logger("account")
        
        if amount <= 0:
            raise ValidationError("扣除金额必须大于0")
        
        account = await self.get_or_create_account(user_id)
        
        # 检查余额
        old_balance = float(account.balance)
        if old_balance < amount:
            raise InsufficientBalanceError(f"余额不足，当前余额：{old_balance}元，需要：{amount}元")
        
        # 计算新余额
        new_balance = old_balance - amount
        
        logger.info(f"[DeductBalance] Deducting: user_id={user_id}, amount={amount}, {old_balance} - {amount} = {new_balance}")
        
        # 更新账户
        account.balance = str(new_balance)
        account.total_consume = str(float(account.total_consume) + amount)
        
        # 创建账单记录
        bill = Bill(
            user_id=uuid.UUID(user_id),
            bill_no=self.generate_bill_no(),
            bill_type=source_type,
            amount=str(-amount),  # 负数表示支出
            balance_before=str(old_balance),
            balance_after=str(new_balance),
            source_type=source_type,
            source_id=source_id,
            description=description,
            status="completed",
            completed_at=datetime.utcnow(),
        )
        self.db.add(bill)
        
        # 【修复】只 flush 不 commit，由调用者统一管理事务
        await self.db.flush()
        logger.info(f"[DeductBalance] Flushed: balance={account.balance}, bill_no={bill.bill_no}")
        
        return account, bill
    
    async def freeze_balance(self, user_id: str, amount: float, source_id: str) -> Account:
        """
        冻结账户余额
        
        Args:
            user_id: 用户ID
            amount: 冻结金额
            source_id: 来源ID（如订单号）
            
        Returns:
            更新后的账户
        """
        if amount <= 0:
            raise ValidationError("冻结金额必须大于0")
        
        account = await self.get_or_create_account(user_id)
        
        available = float(account.balance) - float(account.frozen_balance)
        if available < amount:
            raise InsufficientBalanceError(f"可用余额不足，无法冻结{amount}元")
        
        account.frozen_balance = str(float(account.frozen_balance) + amount)
        
        await self.db.commit()
        await self.db.refresh(account)
        
        return account
    
    async def unfreeze_balance(self, user_id: str, amount: float, source_id: str) -> Account:
        """
        解冻账户余额
        
        Args:
            user_id: 用户ID
            amount: 解冻金额
            source_id: 来源ID
            
        Returns:
            更新后的账户
        """
        if amount <= 0:
            raise ValidationError("解冻金额必须大于0")
        
        account = await self.get_or_create_account(user_id)
        
        if float(account.frozen_balance) < amount:
            raise ValidationError(f"冻结余额不足，无法解冻{amount}元")
        
        account.frozen_balance = str(float(account.frozen_balance) - amount)
        
        await self.db.commit()
        await self.db.refresh(account)
        
        return account
    
    async def get_bill_history(
        self,
        user_id: str,
        bill_type: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Bill], int]:
        """
        获取账单历史
        
        Args:
            user_id: 用户ID
            bill_type: 账单类型筛选
            start_date: 开始日期
            end_date: 结束日期
            page: 页码
            page_size: 每页数量
            
        Returns:
            (账单列表, 总数)
        """
        query = select(Bill).where(Bill.user_id == uuid.UUID(user_id))
        
        if bill_type:
            query = query.where(Bill.bill_type == bill_type)
        if start_date:
            query = query.where(Bill.created_at >= start_date)
        if end_date:
            query = query.where(Bill.created_at <= end_date)
        
        # 统计总数
        count_query = select(func.count(Bill.id)).where(Bill.user_id == uuid.UUID(user_id))
        if bill_type:
            count_query = count_query.where(Bill.bill_type == bill_type)
        if start_date:
            count_query = count_query.where(Bill.created_at >= start_date)
        if end_date:
            count_query = count_query.where(Bill.created_at <= end_date)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 分页查询
        query = query.order_by(Bill.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        bills = result.scalars().all()
        
        return bills, total
    
    async def get_account_summary(self, user_id: str) -> dict:
        """
        获取账户摘要信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            账户摘要
        """
        account = await self.get_or_create_account(user_id)
        
        balance = float(account.balance)
        frozen = float(account.frozen_balance)
        available = balance - frozen
        total_recharge = float(account.total_recharge)
        total_consume = float(account.total_consume)
        
        return {
            "user_id": user_id,
            "balance": balance,
            "frozen_balance": frozen,
            "available_balance": available,
            "total_recharge": total_recharge,
            "total_consume": total_consume,
        }
