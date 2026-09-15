"""
Analytics - 调用/收入趋势（GET /analytics/trend）

拆分自原 `src/api/v1/analytics.py`（P1-4），**函数体逐字未变**，仅移动位置。
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.analytics._shared import (
    ANALYTICS_CACHE_TTL_SECONDS,
    cache_scope,
    check_analytics_permission,
    get_user_repo_ids,
    is_admin_user,
)
from src.config.database import get_db
from src.core.cache import cache_get_json, cache_set_json, make_key
from src.models.user import User
from src.schemas.response import BaseResponse
from src.services.auth_service import get_current_user
from src.services.stats_query_service import PERIOD_DAY, PERIOD_HOUR, StatsQueryService
from src.utils.time_range import cst_now, utc_now

router = APIRouter()


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
    
    now = cst_now()
    
    # 获取用户可访问的仓库
    user_repo_ids = await get_user_repo_ids(db, current_user)
    
    # 仓库过滤范围（StatsQueryService 的 repo_ids 语义：None = 不限制）
    # 说明：沿用既有行为 —— repo_id 过滤只在"开发者"分支生效，
    #       管理员传 repo_id 时仍返回全局口径（历史行为，本次不改变）。
    scope_repo_ids = user_repo_ids
    if user_repo_ids is not None:
        if repo_id:
            # 指定了特定仓库，需要验证是否有权限访问
            try:
                repo_uuid = uuid.UUID(repo_id)
            except ValueError:
                # 【安全修复】原实现在非法 UUID 时 `pass` → 过滤条件为空 →
                #   开发者会拿到**全部仓库**的数据（越权泄露）。改为显式 400。
                return BaseResponse(code=400, message="无效的仓库ID")
            if repo_uuid not in user_repo_ids:
                return BaseResponse(code=403, message="无权访问该仓库的数据")
            scope_repo_ids = [repo_uuid]
        elif not user_repo_ids:
            # 用户没有仓库，返回空数据
            return BaseResponse(data={
                "labels": [],
                "series": {"calls": [], "revenue": []},
                "period": period,
                "days": days,
                "repo_id": repo_id,
                "is_admin_view": False,
                "generated_at": utc_now().isoformat(),
            })
    
    # 按周期分组（口径不变：hour → 最近 24 小时按小时；其它 → 最近 days 天按天）
    if period == "hour":
        start_time = now - timedelta(hours=24)
        granularity = PERIOD_HOUR
    else:
        start_time = now - timedelta(days=days)
        granularity = PERIOD_DAY

    # 【P1-6 阶段 3】结果缓存 60 秒（key 含可见范围与查询参数）
    cache_key = make_key(
        "analytics", "trend", cache_scope(current_user, scope_repo_ids),
        period, days, repo_id or "-",
    )
    cached = await cache_get_json(cache_key)
    if cached is not None:
        return BaseResponse(data=cached)

    # 【P1-6 阶段 2】趋势数据：预聚合段 + 实时段自动合并（数值与改造前一致）
    rows = await StatsQueryService(db).group_by_period(
        start_time, now, granularity, scope_repo_ids
    )

    # 构建数据（label 规则与原实现保持一致：datetime → 时/日格式，date → 字符串）
    labels = []
    calls_data = []
    revenue_data = []
    
    for row in rows:
        period_value = row["key"]
        if isinstance(period_value, datetime):
            if period == "hour":
                labels.append(period_value.strftime("%H:00"))
            else:
                labels.append(period_value.strftime("%m-%d"))
        else:
            labels.append(str(period_value))
        calls_data.append(int(row["calls"] or 0))
        revenue_data.append(float(row["cost"] or 0))
    
    data = {
        "labels": labels,
        "series": {
            "calls": calls_data,
            "revenue": [round(r, 2) for r in revenue_data],
        },
        "period": period,
        "days": days,
        "repo_id": repo_id,
        "is_admin_view": is_admin_user(current_user),
        "generated_at": utc_now().isoformat(),
    }
    await cache_set_json(cache_key, data, ttl=ANALYTICS_CACHE_TTL_SECONDS)
    return BaseResponse(data=data)
