"""
计费接口 —— 账户信息与充值

由 `scripts/dev/split_api_router.py` 从 `src/api/v1/billing.py` 精确搬移生成，
函数体与原实现逐字一致（仅移动位置）。
"""

from datetime import datetime, timezone
from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Numeric
from decimal import Decimal
from src.config.database import get_db
from src.schemas.response import BaseResponse
from src.schemas.request import BillRecharge
from src.services.auth_service import get_current_user
from src.models.user import User
from src.models.billing import Account, Bill, APICallLog
from src.models.repository import Repository
from src.core.exceptions import APIError
from src.config.logging_config import get_logger

logger = get_logger("billing")

router = APIRouter()




@router.get("/account", response_model=BaseResponse[dict])
async def get_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户账户信息
    """
    from src.config.settings import settings
    
    # 查询账户（查找 balance 类型的账户）
    result = await db.execute(
        select(Account).where(
            Account.user_id == current_user.id,
            Account.account_type == "balance"
        )
    )
    # 安全处理：使用 scalars().all() 检查多记录情况
    accounts = result.scalars().all()
    if len(accounts) > 1:
        logger.warning(f"用户 {current_user.id} 存在多个 balance 账户，取第一条")
        account = accounts[0]
    elif len(accounts) == 0:
        account = None
    else:
        account = accounts[0]
    
    if not account:
        # 如果没有账户，创建一个
        account = Account(
            user_id=current_user.id,
            account_type="balance",
            balance="0",
            frozen_balance="0",
            total_recharge="0",
            total_consume="0",
        )
        db.add(account)
        await db.commit()  # 需要 commit 才能持久化
        await db.refresh(account)
        logger.info(f"[Billing] Created new account for user {current_user.id}: balance={account.balance}")
    
    # 计算 API 调用总收益 (从 api_call_logs.cost 字段，按仓库所有者关联)
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(func.cast(APICallLog.cost, Numeric)), 0)).join(
            Repository, APICallLog.repo_id == Repository.id
        ).where(Repository.owner_id == current_user.id)
    )
    total_revenue = float(revenue_result.scalar() or 0)
    
    return BaseResponse(
        data={
            "id": str(account.id),
            "user_id": str(account.user_id),
            "balance": float(account.balance or 0),
            "frozen_balance": float(account.frozen_balance or 0),
            "total_recharge": float(account.total_recharge or 0),
            "total_consumption": float(account.total_consume or 0),
            "total_revenue": total_revenue,  # API 调用总收益（按仓库所有者计算）
            "created_at": account.created_at.isoformat() if account.created_at else None,
            "mock_mode": settings.payment_mock_mode,
            "environment": settings.billing_environment,
        }
    )


@router.post("/recharge", response_model=BaseResponse[dict])
async def recharge(
    recharge_data: BillRecharge,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    充值接口（实际充值）
    
    【注意】此接口是直接充值接口，不经过支付回调流程。
    充值后余额直接增加。
    """
    from src.config.settings import settings
    import uuid
    
    try:
        # 查找或创建账户
        result = await db.execute(
            select(Account).where(
                Account.user_id == current_user.id,
                Account.account_type == "balance"
            )
        )
        # 安全处理：使用 scalars().all() 检查多记录情况
        accounts = result.scalars().all()
        if len(accounts) > 1:
            logger.warning(f"用户 {current_user.id} 存在多个 balance 账户，取第一条")
            account = accounts[0]
        elif len(accounts) == 0:
            account = None
        else:
            account = accounts[0]
        
        # 账户不存在则创建
        if not account:
            account = Account(
                user_id=current_user.id,
                account_type="balance",
                balance="0",
                frozen_balance="0",
                total_recharge="0",
                total_consume="0",
            )
            db.add(account)
            await db.flush()  # 先 flush 获取 ID
            logger.info(f"[Recharge] Created new account for user {current_user.id}")
        
        # 计算新余额
        amount = str(recharge_data.amount)
        old_balance = Decimal(account.balance or "0")
        new_balance = old_balance + Decimal(amount)
        
        # 确定环境标识（唯一数据源：settings.billing_environment）
        environment = settings.billing_environment
        
        # 创建账单记录
        bill_no = f"RE{int(uuid.uuid1().time_low):010d}"
        bill = Bill(
            user_id=current_user.id,
            bill_no=bill_no,
            bill_type="recharge",
            amount=amount,
            balance_before=str(old_balance),
            balance_after=str(new_balance),
            source_type="manual",
            description=f"账户充值: {recharge_data.amount}元",
            remark=recharge_data.remark,
            payment_method=recharge_data.payment_method,
            status="completed",
            completed_at=datetime.now(timezone.utc),
            environment=environment,
        )
        db.add(bill)
        
        # 更新账户
        account.balance = str(new_balance)
        account.total_recharge = str(Decimal(account.total_recharge or "0") + Decimal(amount))
        
        # 提交事务确保数据持久化
        await db.commit()
        await db.refresh(account)
        await db.refresh(bill)
        logger.info(f"[Recharge] 充值成功: user_id={current_user.id}, amount={amount}, new_balance={account.balance}")
        
        return BaseResponse(
            data={
                "order_id": bill_no,
                "balance": float(account.balance),
                "environment": environment,
            }
        )
    except Exception as e:
        logger.error(f"[Recharge] 充值失败: user_id={current_user.id}, error={e}", exc_info=True)
        await db.rollback()
        raise APIError(f"充值失败: {str(e)}")
