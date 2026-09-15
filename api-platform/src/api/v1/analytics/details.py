"""
Analytics - 仓库明细（GET /analytics/repo-details）

拆分自原 `src/api/v1/analytics.py`（P1-4），**函数体逐字未变**，仅移动位置。
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
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
from src.models.repository import Repository
from src.models.user import User
from src.schemas.response import BaseResponse
from src.services.auth_service import get_current_user
from src.services.stats_query_service import StatsQueryService
from src.utils.time_range import utc_now

router = APIRouter()


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
    
    # 【P1-6 阶段 3】结果缓存 60 秒（key 含可见范围 + 分页/筛选/排序参数）
    cache_key = make_key(
        "analytics", "repo-details", cache_scope(current_user, user_repo_ids),
        page, page_size, status or "-", sort_by, sort_order,
    )
    cached = await cache_get_json(cache_key)
    if cached is not None:
        return BaseResponse(data=cached)

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

    # 【P1-6 阶段 2】批量统计：一次分组拿到本页所有仓库的调用/成功/成本
    #   替代原先"每个仓库各查 3 次"的 N×3 查询（20 个仓库：60 条 SQL → 最多 2 条）。
    #   口径不变（全部时间；成功 = 2xx），数值与改造前逐值一致。
    page_repo_ids = [repo.id for repo in repos]
    metrics_map = (
        await StatsQueryService(db).group_by_repo(
            ALL_TIME_START_UTC, utc_now(), page_repo_ids
        )
        if page_repo_ids else {}
    )

    # 汇总各仓库的统计数据
    items = []
    for repo in repos:
        metrics = metrics_map.get(
            repo.id,
            {"total_calls": 0, "success_calls": 0, "total_cost": Decimal("0")},
        )
        total_calls = int(metrics["total_calls"])
        success_calls = int(metrics["success_calls"])
        total_cost = float(metrics["total_cost"])

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
    
    data = {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        },
        "is_admin_view": is_admin_user(current_user),
        "generated_at": utc_now().isoformat(),
    }
    await cache_set_json(cache_key, data, ttl=ANALYTICS_CACHE_TTL_SECONDS)
    return BaseResponse(data=data)
