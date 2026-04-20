"""Billing API - 计费接口"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, Numeric, DECIMAL
from decimal import Decimal
from pydantic import BaseModel

from src.config.database import get_db
from src.schemas.response import BaseResponse
from src.schemas.request import BillRecharge
from src.services.auth_service import get_current_user
from src.models.user import User
from src.models.billing import Account, Bill, APICallLog, MonthlyBill
from src.models.repository import Repository

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
            "mock_mode": settings.payment_mock_mode,
            "environment": "simulation" if settings.payment_mock_mode else "production",
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
    environment: str = Query(None, description="环境过滤：simulation/production"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取账单列表
    根据当前支付模式自动过滤：模拟模式只显示模拟数据，真实模式只显示真实数据
    """
    from src.config.settings import settings
    
    # 自动判断环境（如果未指定）
    if environment is None:
        environment = "simulation" if settings.payment_mock_mode else "production"
    
    # 构建查询
    query = select(Bill).where(
        Bill.user_id == current_user.id,
        Bill.environment == environment,  # 环境过滤
    )
    
    if bill_type:
        query = query.where(Bill.bill_type == bill_type)
    
    # 获取总数
    count_query = select(func.count(Bill.id)).where(
        Bill.user_id == current_user.id,
        Bill.environment == environment,
    )
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
                    "environment": bill.environment,
                    "created_at": bill.created_at.isoformat() if bill.created_at else None,
                }
                for bill in bills
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            },
            "environment": environment,
            "mock_mode": settings.payment_mock_mode,
        }
    )


@router.get("/monthly-summary", response_model=BaseResponse[dict])
async def get_monthly_summary(
    year: int = Query(None),
    month: int = Query(None),
    environment: str = Query(None, description="环境过滤：simulation/production"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取月度汇总
    根据当前支付模式自动过滤数据
    """
    from datetime import datetime
    from src.config.settings import settings
    
    # 自动判断环境（如果未指定）
    if environment is None:
        environment = "simulation" if settings.payment_mock_mode else "production"
    
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
    
    # 查询充值总额 (amount 是字符串，需要转换) - 带环境过滤
    recharge_result = await db.execute(
        select(func.coalesce(func.sum(func.cast(Bill.amount, Numeric)), 0)).where(
            Bill.user_id == current_user.id,
            Bill.bill_type == "recharge",
            Bill.environment == environment,
            Bill.created_at >= start_date,
            Bill.created_at < end_date,
        )
    )
    total_recharge = float(recharge_result.scalar() or 0)
    
    # 查询消费总额 (amount 是字符串，需要转换) - 带环境过滤
    consume_result = await db.execute(
        select(func.coalesce(func.sum(func.cast(Bill.amount, Numeric)), 0)).where(
            Bill.user_id == current_user.id,
            Bill.bill_type == "consume",
            Bill.environment == environment,
            Bill.created_at >= start_date,
            Bill.created_at < end_date,
        )
    )
    total_consumption = float(consume_result.scalar() or 0)
    
    # 查询账单数量 - 带环境过滤
    count_result = await db.execute(
        select(func.count(Bill.id)).where(
            Bill.user_id == current_user.id,
            Bill.bill_type == "consume",
            Bill.environment == environment,
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
            "environment": environment,
            "mock_mode": settings.payment_mock_mode,
        }
    )


@router.get("/balance-history", response_model=BaseResponse[list])
async def get_balance_history(
    days: int = Query(30, ge=1, le=365),
    environment: str = Query(None, description="环境过滤：simulation/production"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取余额历史
    根据当前支付模式自动过滤数据
    """
    from datetime import datetime, timedelta
    from src.config.settings import settings
    
    # 自动判断环境（如果未指定）
    if environment is None:
        environment = "simulation" if settings.payment_mock_mode else "production"
    
    # 获取最近 N 天的余额变化
    start_date = datetime.now() - timedelta(days=days)
    
    result = await db.execute(
        select(Bill).where(
            Bill.user_id == current_user.id,
            Bill.environment == environment,  # 环境过滤
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


# ==================== 开发者账单查询扩展接口 ====================

class RepositoryUsageItem(BaseModel):
    """按仓库的使用量项"""
    repo_id: str
    repo_name: str
    call_count: int
    total_tokens: int
    total_cost: float


@router.get("/usage", response_model=BaseResponse[dict])
async def get_user_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户的使用情况
    
    从 APICallLog 表统计调用次数和 Token 使用量，按仓库聚合返回。
    """
    # 查询用户的总使用量
    total_query = select(
        func.count(APICallLog.id).label("call_count"),
        func.coalesce(func.sum(APICallLog.tokens_used), 0).label("total_tokens"),
        func.coalesce(func.sum(APICallLog.cost.cast(DECIMAL)), 0).label("total_cost"),
    ).where(APICallLog.user_id == current_user.id)
    
    total_result = await db.execute(total_query)
    total_data = total_result.first()
    
    # 查询按仓库的使用量
    by_repo_query = (
        select(
            APICallLog.repo_id,
            func.count(APICallLog.id).label("call_count"),
            func.coalesce(func.sum(APICallLog.tokens_used), 0).label("total_tokens"),
            func.coalesce(func.sum(APICallLog.cost.cast(DECIMAL)), 0).label("total_cost"),
        )
        .where(APICallLog.user_id == current_user.id)
        .group_by(APICallLog.repo_id)
    )
    repo_result = await db.execute(by_repo_query)
    repo_data = repo_result.all()
    
    # 获取仓库名称
    repo_ids = [r.repo_id for r in repo_data if r.repo_id]
    repo_name_map = {}
    if repo_ids:
        repo_query = select(Repository.id, Repository.name).where(Repository.id.in_(repo_ids))
        repo_result = await db.execute(repo_query)
        for row in repo_result.all():
            repo_name_map[row.id] = row.name
    
    # 构建按仓库的使用量列表
    by_repository = []
    for item in repo_data:
        by_repository.append(RepositoryUsageItem(
            repo_id=str(item.repo_id) if item.repo_id else "",
            repo_name=repo_name_map.get(item.repo_id, "Unknown"),
            call_count=item.call_count or 0,
            total_tokens=item.total_tokens or 0,
            total_cost=float(item.total_cost or 0),
        ))
    
    return BaseResponse(
        data={
            "call_count": total_data.call_count or 0,
            "total_tokens": total_data.total_tokens or 0,
            "total_cost": float(total_data.total_cost or 0),
            "by_repository": [item.model_dump() for item in by_repository],
        }
    )


@router.get("/consumption-details", response_model=BaseResponse[dict])
async def get_consumption_details(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    repo_id: Optional[str] = Query(None, description="仓库ID筛选"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户的消费明细
    
    从 APICallLog 表查询详细调用记录，支持分页和筛选。
    """
    from datetime import datetime
    
    # 构建查询条件
    conditions = [APICallLog.user_id == current_user.id]
    
    if repo_id:
        try:
            from uuid import UUID
            rid = UUID(repo_id)
            conditions.append(APICallLog.repo_id == rid)
        except ValueError:
            pass  # 忽略无效的UUID
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            conditions.append(APICallLog.created_at >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            conditions.append(APICallLog.created_at <= end_dt)
        except ValueError:
            pass
    
    # 查询总数
    count_query = select(func.count(APICallLog.id)).where(*conditions)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # 查询调用记录
    query = (
        select(APICallLog, Repository.name.label("repo_name"))
        .outerjoin(Repository, APICallLog.repo_id == Repository.id)
        .where(*conditions)
        .order_by(desc(APICallLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    rows = result.all()
    
    # 构建响应数据
    items = []
    for call_log, repo_name in rows:
        items.append({
            "id": call_log.id,
            "repo_id": str(call_log.repo_id) if call_log.repo_id else None,
            "repo_name": repo_name,
            "endpoint": call_log.endpoint,
            "tokens_used": call_log.tokens_used or 0,
            "cost": float(call_log.cost or 0),
            "created_at": call_log.created_at.isoformat() if call_log.created_at else None,
        })
    
    return BaseResponse(
        data={
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
            },
        }
    )


# ==================== 开发者月度账单接口 ====================

@router.get("/monthly-bills", response_model=BaseResponse[dict])
async def get_my_monthly_bills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    year: Optional[int] = Query(None, description="年份"),
    month: Optional[int] = Query(None, description="月份"),
    status: Optional[str] = Query(None, description="账单状态: pending/generated/reviewed/published"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户的月度账单列表
    只返回已发布的账单或当前用户生成的账单
    """
    from src.config.settings import settings

    environment = "simulation" if settings.payment_mock_mode else "production"

    # 构建查询 - 用户只能查看自己已发布或自己生成的账单
    query = select(MonthlyBill).where(
        MonthlyBill.user_id == current_user.id,
        MonthlyBill.environment == environment,
    )

    # 应用筛选条件
    if year:
        query = query.where(MonthlyBill.year == year)
    if month:
        query = query.where(MonthlyBill.month == month)
    if status:
        query = query.where(MonthlyBill.status == status)

    # 获取总数
    count_query = select(func.count(MonthlyBill.id)).where(
        MonthlyBill.user_id == current_user.id,
        MonthlyBill.environment == environment,
    )
    if year:
        count_query = count_query.where(MonthlyBill.year == year)
    if month:
        count_query = count_query.where(MonthlyBill.month == month)
    if status:
        count_query = count_query.where(MonthlyBill.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    offset = (page - 1) * page_size
    query = query.order_by(desc(MonthlyBill.year), desc(MonthlyBill.month))
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    bills = result.scalars().all()

    return BaseResponse(
        data={
            "items": [
                {
                    "id": str(bill.id),
                    "year": bill.year,
                    "month": bill.month,
                    "total_recharge": float(bill.total_recharge or 0),
                    "total_consumption": float(bill.total_consumption or 0),
                    "net_change": float(bill.net_change or 0),
                    "beginning_balance": float(bill.beginning_balance or 0),
                    "ending_balance": float(bill.ending_balance or 0),
                    "total_calls": bill.total_calls or 0,
                    "total_tokens": bill.total_tokens or 0,
                    "status": bill.status,
                    "generated_at": bill.generated_at.isoformat() if bill.generated_at else None,
                    "published_at": bill.published_at.isoformat() if bill.published_at else None,
                }
                for bill in bills
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            },
            "environment": environment,
        }
    )


@router.get("/monthly-bills/{bill_id}", response_model=BaseResponse[dict])
async def get_my_monthly_bill_detail(
    bill_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户指定月度账单的详情
    """
    import json
    from src.config.settings import settings

    environment = "simulation" if settings.payment_mock_mode else "production"

    # 查询账单
    result = await db.execute(
        select(MonthlyBill).where(
            MonthlyBill.id == bill_id,
            MonthlyBill.user_id == current_user.id,
            MonthlyBill.environment == environment,
        )
    )
    bill = result.scalar_one_or_none()

    if not bill:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Monthly bill not found")

    # 解析详情JSON
    details = {}
    if bill.details:
        try:
            details = json.loads(bill.details)
        except:
            details = {}

    return BaseResponse(
        data={
            "id": str(bill.id),
            "year": bill.year,
            "month": bill.month,
            "total_recharge": float(bill.total_recharge or 0),
            "total_consumption": float(bill.total_consumption or 0),
            "net_change": float(bill.net_change or 0),
            "beginning_balance": float(bill.beginning_balance or 0),
            "ending_balance": float(bill.ending_balance or 0),
            "total_calls": bill.total_calls or 0,
            "total_tokens": bill.total_tokens or 0,
            "details": details,
            "status": bill.status,
            "review_comment": bill.review_comment,
            "reviewed_at": bill.reviewed_at.isoformat() if bill.reviewed_at else None,
            "generated_at": bill.generated_at.isoformat() if bill.generated_at else None,
            "published_at": bill.published_at.isoformat() if bill.published_at else None,
        }
    )


@router.get("/monthly-bills/available-periods", response_model=BaseResponse[list])
async def get_my_available_periods(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户有账单的年月列表
    """
    from src.config.settings import settings

    environment = "simulation" if settings.payment_mock_mode else "production"

    # 查询所有不同的年月
    query = (
        select(MonthlyBill.year, MonthlyBill.month)
        .where(
            MonthlyBill.user_id == current_user.id,
            MonthlyBill.environment == environment,
        )
        .distinct()
        .order_by(desc(MonthlyBill.year), desc(MonthlyBill.month))
    )
    result = await db.execute(query)
    rows = result.all()

    periods = [{"year": row[0], "month": row[1]} for row in rows]

    return BaseResponse(data=periods)
