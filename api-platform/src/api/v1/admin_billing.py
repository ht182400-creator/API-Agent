"""Admin Billing API - 管理员账单管理接口"""

import json
import uuid as uuid_lib
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from src.config.database import get_db
from src.schemas.response import BaseResponse
from src.models.user import User
from src.models.billing import Account, Bill, APICallLog, MonthlyBill
from src.models.repository import Repository
from src.services.auth_service import get_current_user

router = APIRouter()


@router.get("/accounts", response_model=BaseResponse[dict])
async def get_all_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = Query(None, description="按用户ID筛选"),
    environment: Optional[str] = Query(None, description="环境过滤：simulation/production"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取所有用户账户列表
    仅限管理员使用
    """
    from src.config.settings import settings
    from decimal import Decimal
    
    # 自动判断环境
    if environment is None:
        environment = "simulation" if settings.payment_mock_mode else "production"
    
    # 构建基础查询 - 关联用户信息
    query = (
        select(Account, User.username, User.email)
        .join(User, Account.user_id == User.id, isouter=True)
        .where(Account.account_type == "balance")
    )
    
    # 应用筛选条件
    if user_id:
        query = query.where(Account.user_id == user_id)
    
    # 获取总数
    count_query = select(func.count(Account.id)).where(Account.account_type == "balance")
    if user_id:
        count_query = count_query.where(Account.user_id == user_id)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    offset = (page - 1) * page_size
    query = query.order_by(desc(Account.created_at)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    rows = result.all()
    
    # 格式化返回数据
    items = []
    for row in rows:
        account = row[0]
        username = row[1]
        email = row[2]
        items.append({
            "id": str(account.id),
            "user_id": str(account.user_id),
            "username": username or "Unknown",
            "email": email or "",
            "balance": float(account.balance or 0),
            "frozen_balance": float(account.frozen_balance or 0),
            "total_recharge": float(account.total_recharge or 0),
            "total_consume": float(account.total_consume or 0),
            "environment": environment,
            "created_at": account.created_at.isoformat() if account.created_at else None,
        })
    
    return BaseResponse(
        data={
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            },
            "environment": environment,
        }
    )


@router.get("/usage", response_model=BaseResponse[dict])
async def get_all_usage(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = Query(None, description="按用户ID筛选"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    environment: Optional[str] = Query(None, description="环境过滤"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取所有用户的使用情况
    从 APICallLog 表统计调用次数、Token使用量、消费金额
    """
    from src.config.settings import settings
    from decimal import Decimal
    
    # 自动判断环境
    if environment is None:
        environment = "simulation" if settings.payment_mock_mode else "production"
    
    # 日期范围处理
    start_dt = None
    end_dt = None
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
    
    # 构建查询 - 按用户聚合
    base_conditions = []
    if user_id:
        base_conditions.append(APICallLog.user_id == user_id)
    if start_dt:
        base_conditions.append(APICallLog.created_at >= start_dt)
    if end_dt:
        base_conditions.append(APICallLog.created_at <= end_dt)
    
    # 子查询 - 获取每个用户的统计数据
    usage_query = (
        select(
            APICallLog.user_id,
            User.username,
            User.email,
            func.count(APICallLog.id).label("call_count"),
            func.coalesce(func.sum(APICallLog.tokens_used), 0).label("total_tokens"),
            func.coalesce(func.sum(func.cast(APICallLog.cost, __import__('decimal').Decimal)), 0).label("total_cost"),
        )
        .join(User, APICallLog.user_id == User.id, isouter=True)
    )
    
    if base_conditions:
        for cond in base_conditions:
            usage_query = usage_query.where(cond)
    
    usage_query = usage_query.group_by(
        APICallLog.user_id, User.username, User.email
    )
    
    # 获取总数
    count_query = select(func.count()).select_from(usage_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页
    offset = (page - 1) * page_size
    usage_query = usage_query.order_by(desc("call_count")).offset(offset).limit(page_size)
    
    result = await db.execute(usage_query)
    rows = result.all()
    
    # 格式化返回数据
    items = []
    for row in rows:
        items.append({
            "user_id": str(row[0]) if row[0] else None,
            "username": row[1] or "Unknown",
            "email": row[2] or "",
            "call_count": row[3] or 0,
            "total_tokens": row[4] or 0,
            "total_cost": float(row[5] or 0),
        })
    
    return BaseResponse(
        data={
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            },
            "environment": environment,
        }
    )


@router.get("/monthly-bills", response_model=BaseResponse[dict])
async def get_all_monthly_bills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    year: Optional[int] = Query(None, description="年份"),
    month: Optional[int] = Query(None, description="月份"),
    user_id: Optional[str] = Query(None, description="按用户ID筛选"),
    environment: Optional[str] = Query(None, description="环境过滤"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取所有用户的月度账单
    按用户聚合每月的充值、消费数据
    """
    from src.config.settings import settings
    from decimal import Decimal
    
    # 自动判断环境
    if environment is None:
        environment = "simulation" if settings.payment_mock_mode else "production"
    
    # 默认年月
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month
    
    # 计算月份范围
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # 构建查询 - 按用户聚合账单
    query = (
        select(
            Bill.user_id,
            User.username,
            User.email,
            func.coalesce(
                func.sum(func.cast(Bill.amount, Decimal)).filter(Bill.bill_type == "recharge"),
                0
            ).label("recharge_amount"),
            func.coalesce(
                func.sum(func.cast(Bill.amount, Decimal)).filter(Bill.bill_type == "consume"),
                0
            ).label("consume_amount"),
            func.count(Bill.id).label("bill_count"),
        )
        .join(User, Bill.user_id == User.id, isouter=True)
        .where(
            Bill.environment == environment,
            Bill.created_at >= start_date,
            Bill.created_at < end_date,
        )
    )
    
    if user_id:
        query = query.where(Bill.user_id == user_id)
    
    query = query.group_by(Bill.user_id, User.username, User.email)
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页
    offset = (page - 1) * page_size
    query = query.order_by(desc("recharge_amount")).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    rows = result.all()
    
    # 格式化返回数据
    items = []
    for row in rows:
        recharge = float(row[2] or 0)
        consume = abs(float(row[3] or 0))
        items.append({
            "year": year,
            "month": month,
            "user_id": str(row[0]) if row[0] else None,
            "username": row[1] or "Unknown",
            "email": row[2] or "",
            "recharge_amount": recharge,
            "consume_amount": consume,
            "net_change": recharge - consume,
            "bill_count": row[5] or 0,
        })
    
    return BaseResponse(
        data={
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            },
            "year": year,
            "month": month,
            "environment": environment,
        }
    )


@router.get("/statistics", response_model=BaseResponse[dict])
async def get_billing_statistics(
    environment: Optional[str] = Query(None, description="环境过滤"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取账单统计数据概览
    """
    from src.config.settings import settings
    from decimal import Decimal
    
    # 自动判断环境
    if environment is None:
        environment = "simulation" if settings.payment_mock_mode else "production"
    
    # 总充值金额
    recharge_result = await db.execute(
        select(func.coalesce(func.sum(func.cast(Bill.amount, Decimal)), 0)).where(
            Bill.bill_type == "recharge",
            Bill.environment == environment,
        )
    )
    total_recharge = float(recharge_result.scalar() or 0)
    
    # 总消费金额
    consume_result = await db.execute(
        select(func.coalesce(func.sum(func.cast(Bill.amount, Decimal)), 0)).where(
            Bill.bill_type == "consume",
            Bill.environment == environment,
        )
    )
    total_consume = abs(float(consume_result.scalar() or 0))
    
    # 总账户数
    account_count_result = await db.execute(
        select(func.count(Account.id)).where(Account.account_type == "balance")
    )
    account_count = account_count_result.scalar() or 0
    
    # 总调用次数
    call_count_result = await db.execute(
        select(func.count(APICallLog.id))
    )
    call_count = call_count_result.scalar() or 0
    
    # 总Token使用量
    token_count_result = await db.execute(
        select(func.coalesce(func.sum(APICallLog.tokens_used), 0))
    )
    token_count = token_count_result.scalar() or 0
    
    return BaseResponse(
        data={
            "environment": environment,
            "total_recharge": total_recharge,
            "total_consume": total_consume,
            "net_balance": total_recharge - total_consume,
            "account_count": account_count,
            "total_calls": call_count,
            "total_tokens": token_count,
        }
    )


@router.get("/user/{user_id}/detail", response_model=BaseResponse[dict])
async def get_user_billing_detail(
    user_id: str,
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    environment: Optional[str] = Query(None, description="环境过滤"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定用户的详细账单信息
    """
    from src.config.settings import settings
    from decimal import Decimal
    
    # 自动判断环境
    if environment is None:
        environment = "simulation" if settings.payment_mock_mode else "production"
    
    # 日期范围处理
    start_dt = None
    end_dt = None
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    # 获取用户信息
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        return BaseResponse(
            code=404,
            message="User not found",
            data=None
        )
    
    # 获取账户信息
    account_result = await db.execute(
        select(Account).where(
            Account.user_id == user_id,
            Account.account_type == "balance",
        )
    )
    account = account_result.scalar_one_or_none()
    
    # 构建账单查询条件
    bill_conditions = [
        Bill.user_id == user_id,
        Bill.environment == environment,
    ]
    if start_dt:
        bill_conditions.append(Bill.created_at >= start_dt)
    if end_dt:
        bill_conditions.append(Bill.created_at <= end_dt)
    
    # 充值总额
    recharge_result = await db.execute(
        select(func.coalesce(func.sum(func.cast(Bill.amount, Decimal)), 0)).where(
            *bill_conditions,
            Bill.bill_type == "recharge",
        )
    )
    recharge_amount = float(recharge_result.scalar() or 0)
    
    # 消费总额
    consume_result = await db.execute(
        select(func.coalesce(func.sum(func.cast(Bill.amount, Decimal)), 0)).where(
            *bill_conditions,
            Bill.bill_type == "consume",
        )
    )
    consume_amount = abs(float(consume_result.scalar() or 0))
    
    # 调用统计
    call_conditions = [APICallLog.user_id == user_id]
    if start_dt:
        call_conditions.append(APICallLog.created_at >= start_dt)
    if end_dt:
        call_conditions.append(APICallLog.created_at <= end_dt)
    
    call_count_result = await db.execute(
        select(func.count(APICallLog.id)).where(*call_conditions)
    )
    call_count = call_count_result.scalar() or 0
    
    token_count_result = await db.execute(
        select(func.coalesce(func.sum(APICallLog.tokens_used), 0)).where(*call_conditions)
    )
    token_count = token_count_result.scalar() or 0
    
    cost_result = await db.execute(
        select(func.coalesce(func.sum(func.cast(APICallLog.cost, Decimal)), 0)).where(*call_conditions)
    )
    total_cost = float(cost_result.scalar() or 0)
    
    return BaseResponse(
        data={
            "user_id": user_id,
            "username": user.username,
            "email": user.email,
            "account": {
                "balance": float(account.balance) if account else 0,
                "total_recharge": float(account.total_recharge) if account else 0,
                "total_consume": float(account.total_consume) if account else 0,
            } if account else None,
            "billing": {
                "recharge_amount": recharge_amount,
                "consume_amount": consume_amount,
                "net_change": recharge_amount - consume_amount,
            },
            "usage": {
                "call_count": call_count,
                "total_tokens": token_count,
                "total_cost": total_cost,
            },
            "date_range": {
                "start_date": start_date,
                "end_date": end_date,
            },
            "environment": environment,
        }
    )




# ==================== 月度账单管理 ====================

# 注意：具体路由必须放在参数化路由 /{bill_id} 之前！
@router.get("/monthly-bills/generated", response_model=BaseResponse[dict])
async def get_generated_monthly_bills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    year: Optional[int] = Query(None, description="年份"),
    month: Optional[int] = Query(None, description="月份"),
    user_id: Optional[str] = Query(None, description="按用户ID筛选"),
    status: Optional[str] = Query(None, description="账单状态: pending/generated/reviewed/published"),
    environment: Optional[str] = Query(None, description="环境过滤"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取已生成的月度账单列表
    从 MonthlyBill 表查询
    """
    from src.config.settings import settings

    # 自动判断环境
    if environment is None:
        environment = "simulation" if settings.payment_mock_mode else "production"

    # 构建查询
    query = (
        select(MonthlyBill, User.username, User.email)
        .join(User, MonthlyBill.user_id == User.id, isouter=True)
        .where(MonthlyBill.environment == environment)
    )

    # 应用筛选条件
    if year:
        query = query.where(MonthlyBill.year == year)
    if month:
        query = query.where(MonthlyBill.month == month)
    if user_id:
        query = query.where(MonthlyBill.user_id == user_id)
    if status:
        query = query.where(MonthlyBill.status == status)

    # 获取总数
    count_query = select(func.count(MonthlyBill.id)).where(MonthlyBill.environment == environment)
    if year:
        count_query = count_query.where(MonthlyBill.year == year)
    if month:
        count_query = count_query.where(MonthlyBill.month == month)
    if user_id:
        count_query = count_query.where(MonthlyBill.user_id == user_id)
    if status:
        count_query = count_query.where(MonthlyBill.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    offset = (page - 1) * page_size
    query = query.order_by(desc(MonthlyBill.year), desc(MonthlyBill.month), desc(MonthlyBill.created_at))
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    # 格式化返回数据
    items = []
    for monthly_bill, username, email in rows:
        items.append({
            "id": str(monthly_bill.id),
            "user_id": str(monthly_bill.user_id),
            "username": username or "Unknown",
            "email": email or "",
            "year": monthly_bill.year,
            "month": monthly_bill.month,
            "environment": monthly_bill.environment,
            "total_recharge": float(monthly_bill.total_recharge or 0),
            "total_consumption": float(monthly_bill.total_consumption or 0),
            "net_change": float(monthly_bill.net_change or 0),
            "beginning_balance": float(monthly_bill.beginning_balance or 0),
            "ending_balance": float(monthly_bill.ending_balance or 0),
            "total_calls": monthly_bill.total_calls or 0,
            "total_tokens": monthly_bill.total_tokens or 0,
            "status": monthly_bill.status,
            "reviewed_at": monthly_bill.reviewed_at.isoformat() if monthly_bill.reviewed_at else None,
            "reviewed_by": str(monthly_bill.reviewed_by) if monthly_bill.reviewed_by else None,
            "generated_at": monthly_bill.generated_at.isoformat() if monthly_bill.generated_at else None,
            "published_at": monthly_bill.published_at.isoformat() if monthly_bill.published_at else None,
            "created_at": monthly_bill.created_at.isoformat() if monthly_bill.created_at else None,
        })

    return BaseResponse(
        data={
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            },
            "environment": environment,
        }
    )


# 注意：具体路由 /generate 和 /years-months 必须放在参数化路由 /{bill_id} 之前！
@router.post("/monthly-bills/generate", response_model=BaseResponse[dict])
async def generate_monthly_bill(
    year: int = Query(..., description="年份"),
    month: int = Query(..., description="月份"),
    user_id: Optional[str] = Query(None, description="指定用户ID，不指定则生成所有用户"),
    environment: Optional[str] = Query(None, description="环境过滤"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    生成月度账单
    根据指定年月，从 bills 和 api_call_logs 表统计数据，生成月度汇总账单
    """
    from src.config.settings import settings

    # 验证年月
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Invalid month (1-12)")
    if year < 2020 or year > 2100:
        raise HTTPException(status_code=400, detail="Invalid year")

    # 自动判断环境
    if environment is None:
        environment = "simulation" if settings.payment_mock_mode else "production"

    # 计算月份范围
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    generated_count = 0
    skipped_count = 0
    errors = []

    # 确定要生成的用户列表
    if user_id:
        user_ids = [uuid_lib.UUID(user_id)]
    else:
        # 获取所有有账单的用户
        user_query = select(Bill.user_id).where(
            Bill.environment == environment,
            Bill.created_at >= start_date,
            Bill.created_at < end_date,
        ).distinct()
        user_result = await db.execute(user_query)
        user_ids = [row[0] for row in user_result.all()]

    # 为每个用户生成月度账单
    for uid in user_ids:
        try:
            # 检查是否已存在该月账单
            existing = await db.execute(
                select(MonthlyBill).where(
                    MonthlyBill.user_id == uid,
                    MonthlyBill.year == year,
                    MonthlyBill.month == month,
                    MonthlyBill.environment == environment,
                )
            )
            existing_bill = existing.scalar_one_or_none()

            if existing_bill:
                # 更新现有账单
                bill = existing_bill
                skipped_count += 1
            else:
                # 创建新账单
                bill = MonthlyBill(
                    user_id=uid,
                    year=year,
                    month=month,
                    environment=environment,
                    status="generated",
                    generated_by=current_user.id,
                    generated_at=datetime.utcnow(),
                )
                db.add(bill)
                await db.flush()
                generated_count += 1

            # 获取期初余额（上月末）
            prev_month = month - 1 if month > 1 else 12
            prev_year = year if month > 1 else year - 1
            prev_start = datetime(prev_year, prev_month, 1)
            if prev_month == 12:
                prev_end = datetime(prev_year + 1, 1, 1)
            else:
                prev_end = datetime(prev_year, prev_month + 1, 1)

            # 查询期初余额（使用账单表中的最新余额）
            balance_query = select(Bill.balance_after).where(
                Bill.user_id == uid,
                Bill.environment == environment,
                Bill.created_at < start_date,
            ).order_by(desc(Bill.created_at)).limit(1)
            balance_result = await db.execute(balance_query)
            balance_row = balance_result.first()
            beginning_balance = float(balance_row[0]) if balance_row else 0

            # 查询本月充值总额
            recharge_result = await db.execute(
                select(func.coalesce(func.sum(func.cast(Bill.amount, Decimal)), 0)).where(
                    Bill.user_id == uid,
                    Bill.bill_type.in_(["recharge", "refund"]),
                    Bill.environment == environment,
                    Bill.created_at >= start_date,
                    Bill.created_at < end_date,
                )
            )
            total_recharge = float(recharge_result.scalar() or 0)

            # 查询本月消费总额
            consume_result = await db.execute(
                select(func.coalesce(func.sum(func.abs(func.cast(Bill.amount, Decimal))), 0)).where(
                    Bill.user_id == uid,
                    Bill.bill_type == "consumption",
                    Bill.environment == environment,
                    Bill.created_at >= start_date,
                    Bill.created_at < end_date,
                )
            )
            total_consumption = float(consume_result.scalar() or 0)

            # 查询调用统计
            call_result = await db.execute(
                select(
                    func.count(APICallLog.id).label("call_count"),
                    func.coalesce(func.sum(APICallLog.tokens_used), 0).label("total_tokens"),
                ).where(
                    APICallLog.user_id == uid,
                    APICallLog.created_at >= start_date,
                    APICallLog.created_at < end_date,
                )
            )
            call_row = call_result.first()
            total_calls = call_row.call_count or 0
            total_tokens = call_row.total_tokens or 0

            # 计算期末余额
            ending_balance = beginning_balance + total_recharge - total_consumption

            # 查询按仓库的消费明细
            repo_query = (
                select(
                    APICallLog.repo_id,
                    Repository.name,
                    func.count(APICallLog.id).label("call_count"),
                    func.coalesce(func.sum(APICallLog.tokens_used), 0).label("total_tokens"),
                    func.coalesce(func.sum(func.cast(APICallLog.cost, Decimal)), 0).label("total_cost"),
                )
                .outerjoin(Repository, APICallLog.repo_id == Repository.id)
                .where(
                    APICallLog.user_id == uid,
                    APICallLog.created_at >= start_date,
                    APICallLog.created_at < end_date,
                )
                .group_by(APICallLog.repo_id, Repository.name)
            )
            repo_result = await db.execute(repo_query)
            by_repository = []
            for row in repo_result.all():
                by_repository.append({
                    "repo_id": str(row[0]) if row[0] else None,
                    "repo_name": row[1] or "Unknown",
                    "call_count": row[2] or 0,
                    "total_tokens": int(row[3] or 0),
                    "total_cost": float(row[4] or 0),
                })

            # 更新账单数据
            bill.total_recharge = str(total_recharge)
            bill.total_consumption = str(total_consumption)
            bill.net_change = str(total_recharge - total_consumption)
            bill.beginning_balance = str(beginning_balance)
            bill.ending_balance = str(ending_balance)
            bill.total_calls = total_calls
            bill.total_tokens = total_tokens
            bill.details = json.dumps({
                "by_repository": by_repository,
                "generated_at": datetime.utcnow().isoformat(),
                "period": f"{year}-{month:02d}",
            })

        except Exception as e:
            errors.append({"user_id": str(uid), "error": str(e)})

    await db.commit()

    return BaseResponse(
        data={
            "year": year,
            "month": month,
            "environment": environment,
            "generated_count": generated_count,
            "skipped_count": skipped_count,
            "total_count": generated_count + skipped_count,
            "errors": errors if errors else None,
        }
    )


@router.put("/monthly-bills/{bill_id}/review", response_model=BaseResponse[dict])
async def review_monthly_bill(
    bill_id: str,
    action: str = Query(..., description="审核动作: approve(通过)/reject(拒绝)"),
    comment: Optional[str] = Query(None, description="审核备注"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    审核月度账单
    - approve: 审核通过，状态变为 reviewed
    - reject: 审核拒绝，状态保持不变
    """
    # 查询账单
    result = await db.execute(
        select(MonthlyBill).where(MonthlyBill.id == bill_id)
    )
    bill = result.scalar_one_or_none()

    if not bill:
        raise HTTPException(status_code=404, detail="Monthly bill not found")

    if bill.status not in ["generated", "pending"]:
        raise HTTPException(status_code=400, detail=f"Cannot review bill with status: {bill.status}")

    if action == "approve":
        bill.status = "reviewed"
        bill.reviewed_by = current_user.id
        bill.reviewed_at = datetime.utcnow()
        bill.review_comment = comment
        await db.flush()
        await db.commit()

        return BaseResponse(
            data={
                "id": str(bill.id),
                "status": bill.status,
                "reviewed_by": str(bill.reviewed_by),
                "reviewed_at": bill.reviewed_at.isoformat(),
                "review_comment": bill.review_comment,
            },
            message="Bill approved successfully"
        )

    elif action == "reject":
        # 拒绝不需要改变状态，只记录审核信息
        bill.reviewed_by = current_user.id
        bill.reviewed_at = datetime.utcnow()
        bill.review_comment = comment
        await db.flush()
        await db.commit()

        return BaseResponse(
            data={
                "id": str(bill.id),
                "status": bill.status,
                "reviewed_by": str(bill.reviewed_by),
                "reviewed_at": bill.reviewed_at.isoformat(),
                "review_comment": bill.review_comment,
            },
            message="Bill review recorded (rejected)"
        )

    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")


@router.put("/monthly-bills/{bill_id}/publish", response_model=BaseResponse[dict])
async def publish_monthly_bill(
    bill_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    发布月度账单（发布后用户可见）
    """
    # 查询账单
    result = await db.execute(
        select(MonthlyBill).where(MonthlyBill.id == bill_id)
    )
    bill = result.scalar_one_or_none()

    if not bill:
        raise HTTPException(status_code=404, detail="Monthly bill not found")

    if bill.status == "published":
        raise HTTPException(status_code=400, detail="Bill already published")

    if bill.status != "reviewed":
        raise HTTPException(status_code=400, detail=f"Cannot publish bill with status: {bill.status}. Bill must be reviewed first.")

    bill.status = "published"
    bill.published_at = datetime.utcnow()
    await db.flush()
    await db.commit()

    return BaseResponse(
        data={
            "id": str(bill.id),
            "status": bill.status,
            "published_at": bill.published_at.isoformat(),
        },
        message="Bill published successfully"
    )


@router.get("/monthly-bills/years-months", response_model=BaseResponse[list])
async def get_available_periods(
    environment: Optional[str] = Query(None, description="环境过滤"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取有账单的年月列表（用于选择器）
    """
    from src.config.settings import settings

    # 自动判断环境
    if environment is None:
        environment = "simulation" if settings.payment_mock_mode else "production"

    # 查询所有不同的年月
    query = (
        select(MonthlyBill.year, MonthlyBill.month)
        .where(MonthlyBill.environment == environment)
        .distinct()
        .order_by(desc(MonthlyBill.year), desc(MonthlyBill.month))
    )
    result = await db.execute(query)
    rows = result.all()

    periods = [{"year": row[0], "month": row[1]} for row in rows]

    return BaseResponse(data=periods)


# 参数化路由必须放在具体路由之后！
@router.get("/monthly-bills/{bill_id}", response_model=BaseResponse[dict])
async def get_monthly_bill_detail(
    bill_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取月度账单详情
    """
    # 查询月度账单
    query = (
        select(MonthlyBill, User.username, User.email)
        .join(User, MonthlyBill.user_id == User.id, isouter=True)
        .where(MonthlyBill.id == bill_id)
    )
    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Monthly bill not found")

    monthly_bill, username, email = row

    # 解析详情JSON
    details = {}
    if monthly_bill.details:
        try:
            details = json.loads(monthly_bill.details)
        except:
            details = {}

    return BaseResponse(
        data={
            "id": str(monthly_bill.id),
            "user_id": str(monthly_bill.user_id),
            "username": username or "Unknown",
            "email": email or "",
            "year": monthly_bill.year,
            "month": monthly_bill.month,
            "environment": monthly_bill.environment,
            "total_recharge": float(monthly_bill.total_recharge or 0),
            "total_consumption": float(monthly_bill.total_consumption or 0),
            "net_change": float(monthly_bill.net_change or 0),
            "beginning_balance": float(monthly_bill.beginning_balance or 0),
            "ending_balance": float(monthly_bill.ending_balance or 0),
            "total_calls": monthly_bill.total_calls or 0,
            "total_tokens": monthly_bill.total_tokens or 0,
            "details": details,
            "status": monthly_bill.status,
            "review_comment": monthly_bill.review_comment,
            "reviewed_at": monthly_bill.reviewed_at.isoformat() if monthly_bill.reviewed_at else None,
            "reviewed_by": str(monthly_bill.reviewed_by) if monthly_bill.reviewed_by else None,
            "generated_at": monthly_bill.generated_at.isoformat() if monthly_bill.generated_at else None,
            "generated_by": str(monthly_bill.generated_by) if monthly_bill.generated_by else None,
            "published_at": monthly_bill.published_at.isoformat() if monthly_bill.published_at else None,
            "created_at": monthly_bill.created_at.isoformat() if monthly_bill.created_at else None,
        }
    )
