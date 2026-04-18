"""Billing API - 计费接口"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, Numeric
from decimal import Decimal

from src.config.database import get_db
from src.schemas.response import BaseResponse
from src.schemas.request import BillRecharge
from src.services.auth_service import get_current_user
from src.models.user import User
from src.models.billing import Account, Bill

router = APIRouter()


@router.get("/account", response_model=BaseResponse[dict])
async def get_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户账户信息
    """
    # 查询账户（查找 balance 类型的账户）
    result = await db.execute(
        select(Account).where(
            Account.user_id == current_user.id,
            Account.account_type == "balance"
        )
    )
    account = result.scalar_one_or_none()
    
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
        await db.flush()
    
    return BaseResponse(
        data={
            "id": str(account.id),
            "user_id": str(account.user_id),
            "balance": float(account.balance or 0),
            "frozen_balance": float(account.frozen_balance or 0),
            "total_recharge": float(account.total_recharge or 0),
            "total_consumption": float(account.total_consume or 0),
            "created_at": account.created_at.isoformat() if account.created_at else None,
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
    """
    import uuid
    
    # 查找或创建账户
    result = await db.execute(
        select(Account).where(
            Account.user_id == current_user.id,
            Account.account_type == "balance"
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        account = Account(
            user_id=current_user.id,
            account_type="balance",
            balance="0",
            total_recharge="0",
            total_consume="0",
        )
        db.add(account)
        await db.flush()
    
    # 计算新余额
    amount = str(recharge_data.amount)
    old_balance = Decimal(account.balance or "0")
    new_balance = old_balance + Decimal(amount)
    
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
    )
    db.add(bill)
    
    # 更新账户
    account.balance = str(new_balance)
    account.total_recharge = str(Decimal(account.total_recharge or "0") + Decimal(amount))
    
    await db.flush()
    
    return BaseResponse(
        data={
            "order_id": bill_no,
            "balance": float(account.balance),
        }
    )


@router.get("/bills", response_model=BaseResponse[dict])
async def get_bills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    bill_type: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取账单列表
    """
    # 构建查询
    query = select(Bill).where(Bill.user_id == current_user.id)
    
    if bill_type:
        query = query.where(Bill.bill_type == bill_type)
    
    # 获取总数
    count_query = select(func.count(Bill.id)).where(Bill.user_id == current_user.id)
    if bill_type:
        count_query = count_query.where(Bill.bill_type == bill_type)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    offset = (page - 1) * page_size
    query = query.order_by(desc(Bill.created_at)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    bills = result.scalars().all()
    
    return BaseResponse(
        data={
            "items": [
                {
                    "id": str(bill.id),
                    "account_id": str(bill.user_id),
                    "bill_type": bill.bill_type,
                    "amount": float(bill.amount),
                    "balance_after": float(bill.balance_after),
                    "payment_method": bill.payment_method,
                    "payment_id": bill.transaction_id,
                    "description": bill.description,
                    "created_at": bill.created_at.isoformat() if bill.created_at else None,
                }
                for bill in bills
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            }
        }
    )


@router.get("/monthly-summary", response_model=BaseResponse[dict])
async def get_monthly_summary(
    year: int = Query(None),
    month: int = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取月度汇总
    """
    from datetime import datetime
    
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month
    
    # 计算月份范围 (使用 datetime 对象而非字符串)
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # 查询充值总额 (amount 是字符串，需要转换)
    recharge_result = await db.execute(
        select(func.coalesce(func.sum(func.cast(Bill.amount, Numeric)), 0)).where(
            Bill.user_id == current_user.id,
            Bill.bill_type == "recharge",
            Bill.created_at >= start_date,
            Bill.created_at < end_date,
        )
    )
    total_recharge = float(recharge_result.scalar() or 0)
    
    # 查询消费总额 (amount 是字符串，需要转换)
    consume_result = await db.execute(
        select(func.coalesce(func.sum(func.cast(Bill.amount, Numeric)), 0)).where(
            Bill.user_id == current_user.id,
            Bill.bill_type == "consume",
            Bill.created_at >= start_date,
            Bill.created_at < end_date,
        )
    )
    total_consumption = float(consume_result.scalar() or 0)
    
    # 查询账单数量
    count_result = await db.execute(
        select(func.count(Bill.id)).where(
            Bill.user_id == current_user.id,
            Bill.bill_type == "consume",
            Bill.created_at >= start_date,
            Bill.created_at < end_date,
        )
    )
    consumption_count = count_result.scalar() or 0
    
    return BaseResponse(
        data={
            "year": year,
            "month": month,
            "total_recharge": total_recharge,
            "total_consumption": total_consumption,
            "consumption_count": consumption_count,
            "net_change": total_recharge - total_consumption,
            "by_repository": [],
        }
    )


@router.get("/balance-history", response_model=BaseResponse[list])
async def get_balance_history(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取余额历史
    """
    from datetime import datetime, timedelta
    
    # 获取最近 N 天的余额变化
    # 按天聚合查询
    query = """
        SELECT 
            DATE(created_at) as date,
            balance_after as balance
        FROM bills
        WHERE user_id = :user_id
        AND created_at >= :start_date
        ORDER BY created_at DESC
    """
    
    # 简化版本：获取每天最后一条记录的余额
    start_date = datetime.now() - timedelta(days=days)
    
    result = await db.execute(
        select(Bill).where(
            Bill.user_id == current_user.id,
            Bill.created_at >= start_date,
        ).order_by(desc(Bill.created_at))
    )
    bills = result.scalars().all()
    
    # 按日期分组，取每天最后的余额
    daily_data = {}
    for bill in bills:
        date_str = bill.created_at.strftime("%Y-%m-%d") if bill.created_at else "unknown"
        if date_str not in daily_data:
            daily_data[date_str] = {
                "date": date_str,
                "daily_change": 0,
                "balance": float(bill.balance_after)
            }
            # 计算日变化
            if bill.bill_type == "recharge":
                daily_data[date_str]["daily_change"] += float(bill.amount)
            elif bill.bill_type == "consume":
                daily_data[date_str]["daily_change"] -= float(bill.amount)
    
    return BaseResponse(
        data=list(daily_data.values())[:days]
    )


@router.get("/consumption-trend", response_model=BaseResponse[list])
async def get_consumption_trend(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取消费趋势
    """
    from datetime import datetime, timedelta
    
    start_date = datetime.now() - timedelta(days=days)
    
    # 查询消费账单并按日期聚合
    query = """
        SELECT 
            DATE(created_at) as date,
            SUM(ABS(CAST(amount AS DECIMAL))) as total_amount
        FROM bills
        WHERE user_id = :user_id
        AND bill_type = 'consume'
        AND created_at >= :start_date
        GROUP BY DATE(created_at)
        ORDER BY date
    """
    
    result = await db.execute(
        select(Bill).where(
            Bill.user_id == current_user.id,
            Bill.bill_type == "consume",
            Bill.created_at >= start_date,
        ).order_by(Bill.created_at)
    )
    bills = result.scalars().all()
    
    # 按日期聚合
    daily_data = {}
    for bill in bills:
        date_str = bill.created_at.strftime("%Y-%m-%d") if bill.created_at else "unknown"
        if date_str not in daily_data:
            daily_data[date_str] = {"date": date_str, "amount": 0}
        daily_data[date_str]["amount"] += abs(float(bill.amount))
    
    return BaseResponse(
        data=list(daily_data.values()) if daily_data else [
            {"date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"), "amount": 0}
            for i in range(days, 0, -1)
        ]
    )
