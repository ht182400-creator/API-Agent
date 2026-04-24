"""
Analytics API - 分析报表接口
提供管理员/开发者视角的数据统计和趋势分析
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, or_, Numeric
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth_service import get_current_user
from src.models.user import User
from src.models.repository import Repository
from src.models.billing import APICallLog
from src.models.api_key import APIKey
from src.schemas.response import BaseResponse
from src.services.permission_service import PermissionService
from src.core.exceptions import AuthorizationError
from src.config.database import get_db

router = APIRouter(prefix="/analytics", tags=["Analytics - 分析报表"])


def check_admin_permission(current_user: User):
    """检查是否为管理员"""
    if not PermissionService.is_admin(current_user):
        raise AuthorizationError("需要管理员权限")


def check_analytics_permission(current_user: User):
    """检查是否有数据分析权限（管理员或开发者）"""
    if not PermissionService.is_developer(current_user):
        raise AuthorizationError("需要开发者或管理员权限")


def is_admin_user(current_user: User) -> bool:
    """检查是否为管理员（管理员可看全局数据）"""
    return PermissionService.is_admin(current_user)


async def get_user_repo_ids(db: AsyncSession, current_user: User) -> List[uuid.UUID]:
    """获取用户可以访问的仓库ID列表（非管理员只能访问自己创建的仓库）"""
    if is_admin_user(current_user):
        # 管理员可以访问所有仓库
        return None  # None 表示不限制
    
    # 非管理员只能访问自己创建的仓库
    result = await db.execute(
        select(Repository.id).where(Repository.owner_id == current_user.id)
    )
    return list(result.scalars().all())


# ==================== 概览统计 ====================

@router.get("/overview", response_model=BaseResponse[dict])
async def get_analytics_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取分析概览统计数据
    
    管理员返回全局数据，开发者返回自己的仓库汇总数据
    """
    check_analytics_permission(current_user)
    
    # 当前北京时间
    now = datetime.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # 获取用户可访问的仓库
    user_repo_ids = await get_user_repo_ids(db, current_user)
    
    # 构建调用日志的过滤条件
    def build_call_log_conditions():
        """构建调用日志的过滤条件"""
        conditions = []
        if user_repo_ids is not None:
            conditions.append(APICallLog.repo_id.in_(user_repo_ids))
        return conditions
    
    # 1. 仓库统计
    repos_query = select(Repository)
    if user_repo_ids is not None:
        repos_query = repos_query.where(Repository.id.in_(user_repo_ids))
    repos_result = await db.execute(repos_query)
    all_repos = repos_result.scalars().all()
    total_repos = len(all_repos)
    online_repos = sum(1 for r in all_repos if r.status == "online")
    pending_repos = sum(1 for r in all_repos if r.status == "pending")
    
    # 2. 今日调用统计
    conditions = build_call_log_conditions()
    conditions.append(func.date(APICallLog.created_at) == today)
    today_calls_result = await db.execute(
        select(func.count(APICallLog.id)).where(and_(*conditions))
    )
    today_calls = today_calls_result.scalar() or 0
    
    # 今日成功调用
    conditions = build_call_log_conditions()
    conditions.extend([
        func.date(APICallLog.created_at) == today,
        APICallLog.status_code >= 200,
        APICallLog.status_code < 300
    ])
    today_success_result = await db.execute(
        select(func.count(APICallLog.id)).where(and_(*conditions))
    )
    today_success = today_success_result.scalar() or 0
    
    # 3. 本周调用统计
    conditions = build_call_log_conditions()
    conditions.append(APICallLog.created_at >= week_ago)
    week_calls_result = await db.execute(
        select(func.count(APICallLog.id)).where(and_(*conditions))
    )
    week_calls = week_calls_result.scalar() or 0
    
    # 4. 本月调用统计
    conditions = build_call_log_conditions()
    conditions.append(APICallLog.created_at >= month_ago)
    month_calls_result = await db.execute(
        select(func.count(APICallLog.id)).where(and_(*conditions))
    )
    month_calls = month_calls_result.scalar() or 0
    
    # 5. 总调用统计
    conditions = build_call_log_conditions()
    total_calls_result = await db.execute(
        select(func.count(APICallLog.id)).where(and_(*conditions)) if conditions else
        select(func.count(APICallLog.id))
    )
    total_calls = total_calls_result.scalar() or 0
    
    # 6. 总收入
    conditions = build_call_log_conditions()
    conditions.append(APICallLog.cost != None)
    total_cost_result = await db.execute(
        select(func.sum(func.cast(APICallLog.cost, Numeric))).where(and_(*conditions)) if conditions else
        select(func.sum(func.cast(APICallLog.cost, Numeric)))
    )
    total_cost = float(total_cost_result.scalar() or 0)
    
    # 7. 今日收入
    conditions = build_call_log_conditions()
    conditions.extend([
        func.date(APICallLog.created_at) == today,
        APICallLog.cost != None
    ])
    today_cost_result = await db.execute(
        select(func.sum(func.cast(APICallLog.cost, Numeric))).where(and_(*conditions))
    )
    today_cost = float(today_cost_result.scalar() or 0)
    
    # 8. 本周收入
    conditions = build_call_log_conditions()
    conditions.extend([
        APICallLog.created_at >= week_ago,
        APICallLog.cost != None
    ])
    week_cost_result = await db.execute(
        select(func.sum(func.cast(APICallLog.cost, Numeric))).where(and_(*conditions))
    )
    week_cost = float(week_cost_result.scalar() or 0)
    
    # 9. 本月收入
    conditions = build_call_log_conditions()
    conditions.extend([
        APICallLog.created_at >= month_ago,
        APICallLog.cost != None
    ])
    month_cost_result = await db.execute(
        select(func.sum(func.cast(APICallLog.cost, Numeric))).where(and_(*conditions))
    )
    month_cost = float(month_cost_result.scalar() or 0)
    
    # 10. 活跃用户数（本周有调用的独立用户数）
    conditions = build_call_log_conditions()
    conditions.append(APICallLog.created_at >= week_ago)
    week_users_result = await db.execute(
        select(func.count(func.distinct(APICallLog.user_id))).where(and_(*conditions))
    )
    active_users = week_users_result.scalar() or 0
    
    # 标记是否为管理员视角
    is_admin_view = is_admin_user(current_user)
    
    return BaseResponse(data={
        "repos": {
            "total": total_repos,
            "online": online_repos,
            "pending": pending_repos,
        },
        "calls": {
            "today": today_calls,
            "week": week_calls,
            "month": month_calls,
            "total": total_calls,
            "today_success": today_success,
            "today_failed": today_calls - today_success,
        },
        "revenue": {
            "today": round(today_cost, 2),
            "week": round(week_cost, 2),
            "month": round(month_cost, 2),
            "total": round(total_cost, 2),
        },
        "active_users": active_users,
        "is_admin_view": is_admin_view,  # 标记数据范围
        "generated_at": datetime.now().isoformat(),
    })


# ==================== 趋势数据 ====================

@router.get("/trend", response_model=BaseResponse[dict])
async def get_analytics_trend(
    period: str = Query("day", description="统计周期: day(按小时), week(按天), month(按天)"),
    days: int = Query(7, description="查询天数", ge=1, le=90),
    repo_id: Optional[str] = Query(None, description="仓库ID过滤（可选）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取调用和收入趋势数据
    
    支持按小时/按天统计，可按仓库筛选
    管理员返回全局数据，开发者只返回自己仓库的数据
    """
    check_analytics_permission(current_user)
    
    now = datetime.now()
    
    # 获取用户可访问的仓库
    user_repo_ids = await get_user_repo_ids(db, current_user)
    
    # 构建查询条件
    conditions = []
    
    # 仓库过滤：开发者只能看自己的仓库
    if user_repo_ids is not None:
        if repo_id:
            # 指定了特定仓库，需要验证是否有权限访问
            try:
                repo_uuid = uuid.UUID(repo_id)
                if repo_uuid not in user_repo_ids:
                    return BaseResponse(code=403, message="无权访问该仓库的数据")
                conditions.append(APICallLog.repo_id == repo_uuid)
            except ValueError:
                pass
        else:
            # 未指定仓库，使用用户自己的仓库
            if user_repo_ids:
                conditions.append(APICallLog.repo_id.in_(user_repo_ids))
            else:
                # 用户没有仓库，返回空数据
                return BaseResponse(data={
                    "labels": [],
                    "series": {"calls": [], "revenue": []},
                    "period": period,
                    "days": days,
                    "repo_id": repo_id,
                    "is_admin_view": False,
                    "generated_at": datetime.now().isoformat(),
                })
    
    # 按周期分组
    if period == "hour":
        # 按小时统计（最近24小时）
        start_time = now - timedelta(hours=24)
        group_by = func.date_trunc('hour', APICallLog.created_at)
    else:
        # 按天统计
        start_time = now - timedelta(days=days)
        group_by = func.date(APICallLog.created_at)
    
    conditions.append(APICallLog.created_at >= start_time)
    
    # 调用量趋势
    calls_query = select(
        group_by.label('period'),
        func.count(APICallLog.id).label('calls'),
        func.sum(func.cast(APICallLog.cost, Numeric)).label('cost')
    ).where(and_(*conditions)).group_by(group_by).order_by(group_by)
    
    result = await db.execute(calls_query)
    rows = result.all()
    
    # 构建数据
    labels = []
    calls_data = []
    revenue_data = []
    
    for row in rows:
        period_value = row.period
        if isinstance(period_value, datetime):
            if period == "hour":
                labels.append(period_value.strftime("%H:00"))
            else:
                labels.append(period_value.strftime("%m-%d"))
        else:
            labels.append(str(period_value))
        calls_data.append(row.calls or 0)
        revenue_data.append(float(row.cost or 0))
    
    return BaseResponse(data={
        "labels": labels,
        "series": {
            "calls": calls_data,
            "revenue": [round(r, 2) for r in revenue_data],
        },
        "period": period,
        "days": days,
        "repo_id": repo_id,
        "is_admin_view": is_admin_user(current_user),
        "generated_at": datetime.now().isoformat(),
    })


# ==================== 仓库明细 ====================

@router.get("/repo-details", response_model=BaseResponse[dict])
async def get_analytics_repo_details(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="仓库状态过滤"),
    sort_by: str = Query("total_calls", description="排序字段: total_calls, total_cost, name"),
    sort_order: str = Query("desc", description="排序方向: asc, desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取各仓库的调用和收入明细
    
    返回仓库列表及其统计数据
    管理员返回所有仓库，开发者只返回自己的仓库
    """
    check_analytics_permission(current_user)
    
    # 获取用户可访问的仓库
    user_repo_ids = await get_user_repo_ids(db, current_user)
    
    # 构建查询
    query = select(Repository)
    count_query = select(func.count(Repository.id))
    
    # 非管理员只能看自己的仓库
    if user_repo_ids is not None:
        query = query.where(Repository.id.in_(user_repo_ids))
        count_query = count_query.where(Repository.id.in_(user_repo_ids))
    
    if status:
        query = query.where(Repository.status == status)
        count_query = count_query.where(Repository.status == status)
    
    # 排序
    if sort_by == "name":
        order_col = Repository.display_name if sort_by == "name" else Repository.name
    elif sort_by == "total_cost":
        order_col = Repository.created_at  # 临时用created_at，后续会替换
    else:
        order_col = Repository.created_at
    
    if sort_order == "desc":
        query = query.order_by(order_col.desc())
    else:
        query = query.order_by(order_col.asc())
    
    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # 执行查询
    result = await db.execute(query)
    repos = result.scalars().all()
    
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # 汇总各仓库的统计数据
    items = []
    for repo in repos:
        # 总调用量
        total_calls_result = await db.execute(
            select(func.count(APICallLog.id)).where(
                APICallLog.repo_id == repo.id
            )
        )
        total_calls = total_calls_result.scalar() or 0
        
        # 成功调用
        success_calls_result = await db.execute(
            select(func.count(APICallLog.id)).where(
                and_(
                    APICallLog.repo_id == repo.id,
                    APICallLog.status_code >= 200,
                    APICallLog.status_code < 300
                )
            )
        )
        success_calls = success_calls_result.scalar() or 0
        
        # 总收入
        cost_result = await db.execute(
            select(func.sum(func.cast(APICallLog.cost, Numeric))).where(
                and_(
                    APICallLog.repo_id == repo.id,
                    APICallLog.cost != None
                )
            )
        )
        total_cost = float(cost_result.scalar() or 0)
        
        # 计算成功率
        success_rate = round((success_calls / total_calls * 100), 2) if total_calls > 0 else 0
        
        items.append({
            "repo_id": str(repo.id),
            "name": repo.display_name or repo.name,
            "slug": repo.slug,
            "status": repo.status,
            "owner_id": str(repo.owner_id),
            "total_calls": total_calls,
            "success_calls": success_calls,
            "failed_calls": total_calls - success_calls,
            "success_rate": success_rate,
            "total_cost": round(total_cost, 2),
            "created_at": repo.created_at.isoformat() if repo.created_at else None,
        })
    
    # 按指定字段排序（内存排序）
    if sort_by == "total_calls":
        items.sort(key=lambda x: x["total_calls"], reverse=(sort_order == "desc"))
    elif sort_by == "total_cost":
        items.sort(key=lambda x: x["total_cost"], reverse=(sort_order == "desc"))
    elif sort_by == "name":
        items.sort(key=lambda x: x["name"], reverse=(sort_order == "desc"))
    
    return BaseResponse(data={
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        },
        "is_admin_view": is_admin_user(current_user),
        "generated_at": datetime.now().isoformat(),
    })


# ==================== 仓库趋势 ====================

@router.get("/repo/{repo_id}/trend", response_model=BaseResponse[dict])
async def get_repo_analytics_trend(
    repo_id: str,
    days: int = Query(7, description="查询天数", ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定仓库的调用和收入趋势
    
    开发者只能访问自己创建的仓库
    """
    check_analytics_permission(current_user)
    
    # 验证仓库
    try:
        repo_uuid = uuid.UUID(repo_id)
    except ValueError:
        return BaseResponse(code=400, message="无效的仓库ID")
    
    repo_result = await db.execute(
        select(Repository).where(Repository.id == repo_uuid)
    )
    repo = repo_result.scalar_one_or_none()
    
    if not repo:
        return BaseResponse(code=404, message="仓库不存在")
    
    # 权限检查：开发者只能访问自己的仓库
    if not is_admin_user(current_user) and repo.owner_id != current_user.id:
        return BaseResponse(code=403, message="无权访问该仓库的数据")
    
    now = datetime.now()
    start_time = now - timedelta(days=days)
    
    # 按天统计（response_time是String类型，需转换）
    query = select(
        func.date(APICallLog.created_at).label('date'),
        func.count(APICallLog.id).label('calls'),
        func.sum(func.cast(APICallLog.cost, Numeric)).label('cost'),
        func.avg(func.cast(APICallLog.response_time, Numeric)).label('avg_latency')
    ).where(
        and_(
            APICallLog.repo_id == repo_uuid,
            APICallLog.created_at >= start_time
        )
    ).group_by(func.date(APICallLog.created_at)).order_by(func.date(APICallLog.created_at))
    
    result = await db.execute(query)
    rows = result.all()
    
    labels = []
    calls_data = []
    revenue_data = []
    latency_data = []
    
    for row in rows:
        if isinstance(row.date, datetime):
            labels.append(row.date.strftime("%m-%d"))
        else:
            labels.append(str(row.date))
        calls_data.append(row.calls or 0)
        revenue_data.append(float(row.cost or 0))
        latency_data.append(float(row.avg_latency or 0) if row.avg_latency else 0)
    
    return BaseResponse(data={
        "repo_id": repo_id,
        "repo_name": repo.display_name or repo.name,
        "labels": labels,
        "series": {
            "calls": calls_data,
            "revenue": [round(r, 2) for r in revenue_data],
            "avg_latency": [round(l, 2) for l in latency_data],
        },
        "days": days,
        "generated_at": datetime.now().isoformat(),
    })


# ==================== 用户排行榜 ====================

@router.get("/user-ranking", response_model=BaseResponse[dict])
async def get_user_ranking(
    period: str = Query("week", description="统计周期: today, week, month, all"),
    limit: int = Query(10, description="返回数量", ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户调用量排行榜
    
    管理员返回全局排行，开发者只返回自己仓库相关的用户排行
    """
    check_analytics_permission(current_user)
    
    now = datetime.now()
    
    if period == "today":
        start_time = now - timedelta(days=1)
    elif period == "week":
        start_time = now - timedelta(days=7)
    elif period == "month":
        start_time = now - timedelta(days=30)
    else:
        start_time = datetime(2000, 1, 1)  # 全部时间
    
    # 获取用户可访问的仓库
    user_repo_ids = await get_user_repo_ids(db, current_user)
    
    # 构建查询条件
    conditions = [APICallLog.created_at >= start_time]
    if user_repo_ids is not None:
        conditions.append(APICallLog.repo_id.in_(user_repo_ids))
    
    # 按用户分组统计
    query = select(
        APICallLog.user_id,
        func.count(APICallLog.id).label('total_calls'),
        func.sum(func.cast(APICallLog.cost, Numeric)).label('total_cost')
    ).where(and_(*conditions)).group_by(APICallLog.user_id).order_by(func.count(APICallLog.id).desc()).limit(limit)
    
    result = await db.execute(query)
    rows = result.all()
    
    items = []
    for rank, row in enumerate(rows, 1):
        # 获取用户信息
        user_result = await db.execute(
            select(User).where(User.id == row.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        items.append({
            "rank": rank,
            "user_id": str(row.user_id),
            "user_name": user.name if user else "Unknown",
            "user_email": user.email if user else "",
            "total_calls": row.total_calls or 0,
            "total_cost": float(row.total_cost or 0),
        })
    
    return BaseResponse(data={
        "items": items,
        "period": period,
        "is_admin_view": is_admin_user(current_user),
        "generated_at": datetime.now().isoformat(),
    })


# ==================== 仓库排行榜 ====================

@router.get("/repo-ranking", response_model=BaseResponse[dict])
async def get_repo_ranking(
    period: str = Query("week", description="统计周期: today, week, month, all"),
    limit: int = Query(10, description="返回数量", ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取仓库调用量排行榜
    
    管理员返回所有仓库排行，开发者只返回自己仓库的排行
    """
    check_analytics_permission(current_user)
    
    now = datetime.now()
    
    if period == "today":
        start_time = now - timedelta(days=1)
    elif period == "week":
        start_time = now - timedelta(days=7)
    elif period == "month":
        start_time = now - timedelta(days=30)
    else:
        start_time = datetime(2000, 1, 1)
    
    # 获取用户可访问的仓库
    user_repo_ids = await get_user_repo_ids(db, current_user)
    
    # 构建查询条件
    conditions = [APICallLog.created_at >= start_time]
    if user_repo_ids is not None:
        conditions.append(APICallLog.repo_id.in_(user_repo_ids))
    
    # 按仓库分组统计
    query = select(
        APICallLog.repo_id,
        func.count(APICallLog.id).label('total_calls'),
        func.sum(func.cast(APICallLog.cost, Numeric)).label('total_cost')
    ).where(and_(*conditions)).group_by(APICallLog.repo_id).order_by(func.count(APICallLog.id).desc()).limit(limit)
    
    result = await db.execute(query)
    rows = result.all()
    
    items = []
    for rank, row in enumerate(rows, 1):
        # 获取仓库信息
        repo_result = await db.execute(
            select(Repository).where(Repository.id == row.repo_id)
        )
        repo = repo_result.scalar_one_or_none()
        
        items.append({
            "rank": rank,
            "repo_id": str(row.repo_id),
            "repo_name": repo.display_name or repo.name if repo else "Unknown",
            "repo_slug": repo.slug if repo else "",
            "status": repo.status if repo else "",
            "total_calls": row.total_calls or 0,
            "total_cost": float(row.total_cost or 0),
        })
    
    return BaseResponse(data={
        "items": items,
        "period": period,
        "is_admin_view": is_admin_user(current_user),
        "generated_at": datetime.now().isoformat(),
    })
