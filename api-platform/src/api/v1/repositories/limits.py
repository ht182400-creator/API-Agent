"""
仓库接口 —— 仓库限流配置

由 `scripts/dev/split_api_router.py` 从 `src/api/v1/repositories.py` 精确搬移生成，
函数体与原实现逐字一致（仅移动位置）。
"""

from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.config.database import get_db
from src.schemas.response import BaseResponse
from src.core.exceptions import RepositoryNotFoundError
from src.services.auth_service import get_current_user
from src.models.repository import RepoLimits
from src.schemas.request import LimitsUpdate
from src.api.v1.repositories._shared import _check_repo_owner_permission, _get_repo_by_id

router = APIRouter()




# ==================== 仓库限流配置 API ====================

@router.get("/{repo_id}/limits", response_model=BaseResponse[dict])
async def get_limits(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    获取仓库的限流配置

    Args:
        repo_id: 仓库ID或slug

    Returns:
        限流配置
    """
    repo = await _get_repo_by_id(db, repo_id)
    if not repo:
        raise RepositoryNotFoundError()

    _check_repo_owner_permission(repo, current_user)

    result = await db.execute(
        select(RepoLimits).where(RepoLimits.repo_id == repo.id)
    )
    limits = result.scalar_one_or_none()

    if not limits:
        # 返回默认值
        return BaseResponse(
            data={
                "rpm": 1000,
                "rph": 10000,
                "rpd": 100000,
                "burst_limit": 100,
                "concurrent_limit": 10,
                "request_timeout": 30,
                "connect_timeout": 10,
            }
        )

    return BaseResponse(
        data={
            "rpm": limits.rpm,
            "rph": limits.rph,
            "rpd": limits.rpd,
            "burst_limit": limits.burst_limit,
            "concurrent_limit": limits.concurrent_limit,
            "request_timeout": limits.request_timeout,
            "connect_timeout": limits.connect_timeout,
        }
    )


@router.put("/{repo_id}/limits", response_model=BaseResponse[dict])
async def update_limits(
    repo_id: str,
    limits_data: LimitsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    更新仓库的限流配置

    Args:
        repo_id: 仓库ID或slug
        limits_data: 限流配置数据

    Returns:
        更新后的限流配置
    """
    repo = await _get_repo_by_id(db, repo_id)
    if not repo:
        raise RepositoryNotFoundError()

    _check_repo_owner_permission(repo, current_user)

    # 获取或创建限流配置
    result = await db.execute(
        select(RepoLimits).where(RepoLimits.repo_id == repo.id)
    )
    limits = result.scalar_one_or_none()

    if not limits:
        limits = RepoLimits(repo_id=repo.id)
        db.add(limits)

    # 更新字段
    if limits_data.rpm is not None:
        limits.rpm = limits_data.rpm
    if limits_data.rph is not None:
        limits.rph = limits_data.rph
    if limits_data.rpd is not None:
        limits.rpd = limits_data.rpd
    if limits_data.burst_limit is not None:
        limits.burst_limit = limits_data.burst_limit
    if limits_data.concurrent_limit is not None:
        limits.concurrent_limit = limits_data.concurrent_limit
    if limits_data.request_timeout is not None:
        limits.request_timeout = limits_data.request_timeout
    if limits_data.connect_timeout is not None:
        limits.connect_timeout = limits_data.connect_timeout

    await db.commit()
    await db.refresh(limits)

    return BaseResponse(
        data={
            "rpm": limits.rpm,
            "rph": limits.rph,
            "rpd": limits.rpd,
            "burst_limit": limits.burst_limit,
            "concurrent_limit": limits.concurrent_limit,
            "request_timeout": limits.request_timeout,
            "connect_timeout": limits.connect_timeout,
        }
    )
