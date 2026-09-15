"""
Analytics - 概览统计（GET /analytics/overview）

拆分自原 `src/api/v1/analytics.py`（P1-4），**函数体逐字未变**，仅移动位置。
"""

from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
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
from src.utils.time_range import cst_day_range_utc, cst_now, utc_now

router = APIRouter()


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
    
    # 业务口径基于北京时间（aware）。
    # 原先用 datetime.now()（本地 naive）会被会话时区（UTC）解释，导致统计偏移 8 小时；
    # 改用 cst_now() 后 asyncpg 会按 UTC 正确比较。
    now = cst_now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    # "今日"用北京时间自然日的半开区间（同时可命中 created_at 索引）
    today_start_utc, today_end_utc = cst_day_range_utc()
    
    # 获取用户可访问的仓库
    user_repo_ids = await get_user_repo_ids(db, current_user)

    # 【P1-6 阶段 3】结果缓存 60 秒（key 内含数据可见范围，避免不同用户串号）
    cache_key = make_key("analytics", "overview", cache_scope(current_user, user_repo_ids))
    cached = await cache_get_json(cache_key)
    if cached is not None:
        return BaseResponse(data=cached)

    # 【P1-6 阶段 2】取数统一走 StatsQueryService：预聚合优先 + 实时兜底。
    #   原先这里有 11 条独立的全表 COUNT/SUM（今日/本周/本月/全部 × 调用/成功/收入）；
    #   现在改为 4 次窗口求和（大表只承担"聚合水位之后"的尾部查询），
    #   数值与改造前逐值一致（可加量求和 + 水位诚实，见 StatsQueryService 文档）。

    # 1. 仓库统计
    repos_query = select(Repository)
    if user_repo_ids is not None:
        repos_query = repos_query.where(Repository.id.in_(user_repo_ids))
    all_repos = (await db.execute(repos_query)).scalars().all()
    total_repos = len(all_repos)
    online_repos = sum(1 for r in all_repos if r.status == "online")
    pending_repos = sum(1 for r in all_repos if r.status == "pending")

    stats = StatsQueryService(db)

    # 2/3/4/5. 调用量：今日（北京时间自然日半开区间）/ 本周 / 本月 / 全部
    today_metrics = await stats.sum_metrics(today_start_utc, today_end_utc, user_repo_ids)
    week_metrics = await stats.sum_metrics(week_ago, now, user_repo_ids)
    month_metrics = await stats.sum_metrics(month_ago, now, user_repo_ids)
    total_metrics = await stats.sum_metrics(ALL_TIME_START_UTC, now, user_repo_ids)

    today_calls = today_metrics["total_calls"]
    today_success = today_metrics["success_calls"]
    week_calls = week_metrics["total_calls"]
    month_calls = month_metrics["total_calls"]
    total_calls = total_metrics["total_calls"]

    # 6/7/8/9. 收入（与调用量同窗口）
    total_cost = float(total_metrics["total_cost"])
    today_cost = float(today_metrics["total_cost"])
    week_cost = float(week_metrics["total_cost"])
    month_cost = float(month_metrics["total_cost"])

    # 10. 活跃用户数（本周有调用的独立用户数）
    #     ⚠️ 必须实时查询：独立用户数**不可加**（repo_stats.unique_users 是每仓库每小时的
    #     去重数，跨小时求和会重复计数）—— 见 StatsQueryService.count_distinct_users
    active_users = await stats.count_distinct_users(week_ago, now, user_repo_ids)
    
    # 标记是否为管理员视角
    is_admin_view = is_admin_user(current_user)
    
    data = {
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
        "generated_at": utc_now().isoformat(),
    }
    # 回填缓存（Redis 不可用时静默跳过）
    await cache_set_json(cache_key, data, ttl=ANALYTICS_CACHE_TTL_SECONDS)
    return BaseResponse(data=data)
