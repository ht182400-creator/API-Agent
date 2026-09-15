"""
计费接口 —— 用量统计与消费明细

由 `scripts/dev/split_api_router.py` 从 `src/api/v1/billing.py` 精确搬移生成，
函数体与原实现逐字一致（仅移动位置）。
"""

from typing import Optional
from datetime import datetime
from fastapi import Depends, Query, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, DECIMAL
from pydantic import BaseModel
from src.config.database import get_db
from src.schemas.response import BaseResponse
from src.services.auth_service import get_current_user
from src.models.user import User
from src.models.billing import APICallLog
from src.models.repository import Repository
from src.config.logging_config import get_logger

logger = get_logger("billing")

router = APIRouter()




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
            "request_params": call_log.request_params,  # 请求参数 (JSON字符串)
            "tester": call_log.tester,  # 测试人员
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
