"""
Analytics - 单仓库趋势（GET /analytics/repo/{repo_id}/trend）

拆分自原 `src/api/v1/analytics.py`（P1-4），**函数体逐字未变**，仅移动位置。
"""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Numeric, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.analytics._shared import (
    ANALYTICS_CACHE_TTL_SECONDS,
    check_analytics_permission,
    is_admin_user,
)
from src.config.database import get_db
from src.core.cache import cache_get_json, cache_set_json, make_key
from src.models.billing import APICallLog
from src.models.repository import Repository
from src.models.user import User
from src.schemas.response import BaseResponse
from src.services.auth_service import get_current_user
from src.utils.time_range import cst_date_expr, cst_now, utc_now

router = APIRouter()


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
    
    now = cst_now()
    start_time = now - timedelta(days=days)

    # 【P1-6 阶段 3】结果缓存 60 秒。
    #   key 只含仓库 ID 与天数：权限已在上方校验（非管理员仅自己仓库可见），
    #   同一仓库的趋势数据对所有有权限者一致，不存在越权问题。
    cache_key = make_key("analytics", "repo-trend", str(repo_uuid), days)
    cached = await cache_get_json(cache_key)
    if cached is not None:
        return BaseResponse(data=cached)

    # 按天统计（response_time 是 String 类型，需转换；日期按北京时间取）
    # 说明：本接口只查**单个仓库**（数据量小），且需要 avg_latency ——
    #       时延平均值不可加，无法由 repo_stats 求和还原，因此保持实时查询，不做预聚合读切换。
    # ⚠️ select/group_by/order_by 必须复用**同一表达式对象**：
    #    cst_date_expr 每次调用都会生成新的绑定参数（'Asia/Shanghai' 字面量），
    #    多次调用会让 PostgreSQL 判定 SELECT 与 GROUP BY 不一致 → GroupingError。
    date_col = cst_date_expr(APICallLog.created_at).label('date')
    query = select(
        date_col,
        func.count(APICallLog.id).label('calls'),
        func.sum(func.cast(APICallLog.cost, Numeric)).label('cost'),
        func.avg(func.cast(APICallLog.response_time, Numeric)).label('avg_latency')
    ).where(
        and_(
            APICallLog.repo_id == repo_uuid,
            APICallLog.created_at >= start_time
        )
    ).group_by(date_col).order_by(date_col)
    
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
    
    data = {
        "repo_id": repo_id,
        "repo_name": repo.display_name or repo.name,
        "labels": labels,
        "series": {
            "calls": calls_data,
            "revenue": [round(r, 2) for r in revenue_data],
            "avg_latency": [round(l, 2) for l in latency_data],
        },
        "days": days,
        "generated_at": utc_now().isoformat(),
    }
    await cache_set_json(cache_key, data, ttl=ANALYTICS_CACHE_TTL_SECONDS)
    return BaseResponse(data=data)
