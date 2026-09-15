"""
计费接口 —— 月度账单（列表 / 明细 / 可查周期）

由 `scripts/dev/split_api_router.py` 从 `src/api/v1/billing.py` 精确搬移生成，
函数体与原实现逐字一致（仅移动位置）。
"""

from typing import Optional
from fastapi import Depends, Query, HTTPException, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from src.config.database import get_db
from src.schemas.response import BaseResponse
from src.services.auth_service import get_current_user
from src.models.user import User
from src.models.billing import MonthlyBill
from src.utils.environment import current_environment
from src.config.logging_config import get_logger

logger = get_logger("billing")

router = APIRouter()




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
    # 当前环境标识（唯一数据源）
    environment = current_environment()

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

    # 当前环境标识（唯一数据源）
    environment = current_environment()

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
    # 当前环境标识（唯一数据源）
    environment = current_environment()

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
