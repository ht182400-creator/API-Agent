"""Analytics API - 仓库所有者数据分析API"""

from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, Numeric
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth_service import get_current_user
from src.models.user import User
from src.models.repository import Repository
from src.models.billing import APICallLog
from src.schemas.response import BaseResponse
from src.config.database import get_db

router = APIRouter()


@router.get("/owner/overview", response_model=BaseResponse[dict])
async def get_owner_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取仓库所有者总览统计
    - 总调用次数
    - 总收益
    - 活跃仓库数
    - 本月增长
    """
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 获取用户拥有的仓库
    repo_query = select(func.count(Repository.id)).where(Repository.owner_id == current_user.id)
    repo_result = await db.execute(repo_query)
    total_repos = repo_result.scalar() or 0
    
    # 获取总调用次数
    call_query = select(func.count(APICallLog.id)).join(
        Repository, APICallLog.repo_id == Repository.id
    ).where(Repository.owner_id == current_user.id)
    call_result = await db.execute(call_query)
    total_calls = call_result.scalar() or 0
    
    # 获取本月调用次数
    month_call_query = select(func.count(APICallLog.id)).join(
        Repository, APICallLog.repo_id == Repository.id
    ).where(
        and_(
            Repository.owner_id == current_user.id,
            APICallLog.created_at >= month_start
        )
    )
    month_result = await db.execute(month_call_query)
    month_calls = month_result.scalar() or 0
    
    # 获取总收益 (从 bills 表)
    from src.models.billing import Bill
    revenue_query = select(func.sum(func.cast(Bill.amount, Numeric))).where(
        and_(
            Bill.user_id == current_user.id,
            Bill.bill_type.in_(['recharge', 'bonus']),
            Bill.status == 'completed'
        )
    )
    revenue_result = await db.execute(revenue_query)
    total_revenue = float(revenue_result.scalar() or 0)
    
    return BaseResponse(data={
        "total_calls": total_calls,
        "month_calls": month_calls,
        "total_repos": total_repos,
        "total_revenue": round(total_revenue, 2),
        "growth_rate": round((month_calls / max(total_calls, 1)) * 100, 2) if total_calls > 0 else 0
    })


@router.get("/owner/weekly", response_model=BaseResponse[list])
async def get_weekly_stats(
    weeks: int = Query(default=1, ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取每周调用统计（用于趋势图）
    返回最近N周的每日统计数据
    """
    result = []
    now = datetime.utcnow()
    
    for week in range(weeks):
        week_end = now - timedelta(days=week * 7)
        for day in range(7):
            date = week_end - timedelta(days=day)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date_start + timedelta(days=1)
            
            # 获取当日调用量和收益
            query = select(
                func.count(APICallLog.id).label("calls"),
                func.coalesce(func.sum(func.cast(APICallLog.cost, Numeric)), 0).label("revenue")
            ).join(
                Repository, APICallLog.repo_id == Repository.id
            ).where(
                and_(
                    Repository.owner_id == current_user.id,
                    APICallLog.created_at >= date_start,
                    APICallLog.created_at < date_end
                )
            )
            res = await db.execute(query)
            row = res.one_or_none()
            
            result.append({
                "date": date.strftime("%Y-%m-%d"),
                "calls": row.calls if row else 0,
                "revenue": float(row.revenue) if row else 0
            })
    
    result.reverse()
    return BaseResponse(data=result)


@router.get("/owner/hourly", response_model=BaseResponse[list])
async def get_hourly_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取24小时调用分布
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    result = []
    for hour in range(24):
        hour_start = today_start + timedelta(hours=hour)
        hour_end = hour_start + timedelta(hours=1)
        
        query = select(func.count(APICallLog.id)).join(
            Repository, APICallLog.repo_id == Repository.id
        ).where(
            and_(
                Repository.owner_id == current_user.id,
                APICallLog.created_at >= hour_start,
                APICallLog.created_at < hour_end
            )
        )
        res = await db.execute(query)
        calls = res.scalar() or 0
        
        result.append({
            "hour": f"{hour}:00",
            "calls": calls
        })
    
    return BaseResponse(data=result)


@router.get("/owner/sources", response_model=BaseResponse[list])
async def get_call_sources(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取调用来源分布
    按 source 字段统计
    """
    query = select(
        func.coalesce(APICallLog.source, 'unknown').label("source"),
        func.count(APICallLog.id).label("count")
    ).join(
        Repository, APICallLog.repo_id == Repository.id
    ).where(
        Repository.owner_id == current_user.id
    ).group_by(
        func.coalesce(APICallLog.source, 'unknown')
    ).order_by(
        func.count(APICallLog.id).desc()
    )
    
    res = await db.execute(query)
    rows = res.all()
    
    # 计算百分比
    total = sum(row.count for row in rows) if rows else 1
    
    result = []
    source_names = {
        'web': 'Web',
        'ios': 'iOS', 
        'android': 'Android',
        'api': 'API',
        'unknown': '其他'
    }
    
    for row in rows:
        result.append({
            "name": source_names.get(row.source.lower(), row.source) if row.source else '其他',
            "value": row.count,
            "percentage": round((row.count / total) * 100, 1)
        })
    
    return BaseResponse(data=result)
