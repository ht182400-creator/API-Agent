"""
Analytics - 排行榜（GET /analytics/user-ranking、GET /analytics/repo-ranking）

拆分自原 `src/api/v1/analytics.py`（P1-4），**函数体逐字未变**，仅移动位置。
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Numeric, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.analytics._shared import (
    ALL_TIME_START_UTC,
    ANALYTICS_CACHE_TTL_SECONDS,
    cache_scope,
    check_analytics_permission,
    get_user_repo_ids,
    is_admin_user,
)
from src.config.database import get_db
from src.core.cache import cache_get_json, cache_set_json, make_key
from src.models.billing import APICallLog
from src.models.repository import Repository
from src.models.user import User
from src.schemas.response import BaseResponse
from src.services.auth_service import get_current_user
from src.services.stats_query_service import StatsQueryService
from src.utils.time_range import cst_now, utc_now

router = APIRouter()


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
    
    now = cst_now()
    
    if period == "today":
        start_time = now - timedelta(days=1)
    elif period == "week":
        start_time = now - timedelta(days=7)
    elif period == "month":
        start_time = now - timedelta(days=30)
    else:
        # "全部时间"：使用 aware 锚点（原为 naive datetime(2000,1,1)，顺手消除）
        start_time = ALL_TIME_START_UTC
    
    # 获取用户可访问的仓库
    user_repo_ids = await get_user_repo_ids(db, current_user)

    # 【P1-6 阶段 3】结果缓存 60 秒（key 含可见范围 + period/limit）
    cache_key = make_key(
        "analytics", "user-ranking", cache_scope(current_user, user_repo_ids), period, limit,
    )
    cached = await cache_get_json(cache_key)
    if cached is not None:
        return BaseResponse(data=cached)

    # 说明：用户维度排行**无法**使用 repo_stats 预聚合（该表只有 repo/hour 维度），
    #       因此这里保持实时聚合；本次优化点是消除"逐个查用户信息"的 N+1。
    conditions = [APICallLog.created_at >= start_time, APICallLog.created_at < now]
    if user_repo_ids is not None:
        conditions.append(APICallLog.repo_id.in_(user_repo_ids))
    
    # 按用户分组统计
    query = select(
        APICallLog.user_id,
        func.count(APICallLog.id).label('total_calls'),
        func.sum(func.cast(APICallLog.cost, Numeric)).label('total_cost')
    ).where(and_(*conditions)).group_by(APICallLog.user_id).order_by(func.count(APICallLog.id).desc()).limit(limit)
    
    rows = (await db.execute(query)).all()

    # 用户信息**批量**查询（替代原先逐个查询的 N+1）
    user_ids = [row.user_id for row in rows]
    user_map = {}
    if user_ids:
        user_rows = (await db.execute(
            select(User).where(User.id.in_(user_ids))
        )).scalars().all()
        user_map = {user.id: user for user in user_rows}

    items = []
    for rank, row in enumerate(rows, 1):
        user = user_map.get(row.user_id)
        
        items.append({
            "rank": rank,
            "user_id": str(row.user_id),
            "user_name": user.name if user else "Unknown",
            "user_email": user.email if user else "",
            "total_calls": row.total_calls or 0,
            "total_cost": float(row.total_cost or 0),
        })
    
    data = {
        "items": items,
        "period": period,
        "is_admin_view": is_admin_user(current_user),
        "generated_at": utc_now().isoformat(),
    }
    await cache_set_json(cache_key, data, ttl=ANALYTICS_CACHE_TTL_SECONDS)
    return BaseResponse(data=data)


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
    
    now = cst_now()
    
    if period == "today":
        start_time = now - timedelta(days=1)
    elif period == "week":
        start_time = now - timedelta(days=7)
    elif period == "month":
        start_time = now - timedelta(days=30)
    else:
        # "全部时间"：使用 aware 锚点（原实现用 naive 的 datetime(2000,1,1)，
        # 会被会话时区解释 —— 顺手消除；2000 年前无真实数据，口径等价）
        start_time = ALL_TIME_START_UTC
    
    # 获取用户可访问的仓库
    user_repo_ids = await get_user_repo_ids(db, current_user)

    # 【P1-6 阶段 3】结果缓存 60 秒（key 含可见范围 + period/limit）
    cache_key = make_key(
        "analytics", "repo-ranking", cache_scope(current_user, user_repo_ids), period, limit,
    )
    cached = await cache_get_json(cache_key)
    if cached is not None:
        return BaseResponse(data=cached)

    # 【P1-6 阶段 2】按仓库分组统计（预聚合优先 + 实时兜底），内存排序取前 N
    metrics_map = await StatsQueryService(db).group_by_repo(start_time, now, user_repo_ids)
    ranked = sorted(
        metrics_map.items(),
        key=lambda kv: kv[1]["total_calls"],
        reverse=True,
    )[:limit]

    # 仓库信息**批量**查询（替代原先逐个查询的 N+1）
    ranked_repo_ids = [repo_id for repo_id, _ in ranked]
    repo_map = {}
    if ranked_repo_ids:
        repo_rows = (await db.execute(
            select(Repository).where(Repository.id.in_(ranked_repo_ids))
        )).scalars().all()
        repo_map = {repo.id: repo for repo in repo_rows}

    items = []
    for rank, (repo_id, metrics) in enumerate(ranked, 1):
        repo = repo_map.get(repo_id)

        items.append({
            "rank": rank,
            "repo_id": str(repo_id),
            "repo_name": repo.display_name or repo.name if repo else "Unknown",
            "repo_slug": repo.slug if repo else "",
            "status": repo.status if repo else "",
            "total_calls": int(metrics["total_calls"] or 0),
            "total_cost": float(metrics["total_cost"] or 0),
        })
    
    data = {
        "items": items,
        "period": period,
        "is_admin_view": is_admin_user(current_user),
        "generated_at": utc_now().isoformat(),
    }
    await cache_set_json(cache_key, data, ttl=ANALYTICS_CACHE_TTL_SECONDS)
    return BaseResponse(data=data)
