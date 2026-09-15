"""
仓库接口 —— 仓库端点配置（列表 / 增删改 / 批量）

由 `scripts/dev/split_api_router.py` 从 `src/api/v1/repositories.py` 精确搬移生成，
函数体与原实现逐字一致（仅移动位置）。
"""

from typing import List
from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.config.database import get_db
from src.schemas.response import BaseResponse
from src.core.exceptions import RepositoryNotFoundError
from src.services.auth_service import get_current_user
from src.models.repository import RepoEndpoint
from src.schemas.request import EndpointCreate, EndpointUpdate, EndpointsBatchUpdate
from uuid import UUID
from src.api.v1.repositories._shared import _check_repo_owner_permission, _get_repo_by_id

router = APIRouter()




@router.get("/{repo_id}/endpoints", response_model=BaseResponse[List[dict]])
async def list_endpoints(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    获取仓库的所有API端点

    Args:
        repo_id: 仓库ID或slug

    Returns:
        端点列表
    """
    repo = await _get_repo_by_id(db, repo_id)
    if not repo:
        raise RepositoryNotFoundError()

    _check_repo_owner_permission(repo, current_user)

    result = await db.execute(
        select(RepoEndpoint).where(
            RepoEndpoint.repo_id == repo.id
        ).order_by(RepoEndpoint.display_order)
    )
    endpoints = result.scalars().all()

    return BaseResponse(
        data=[
            {
                "id": str(ep.id),
                "path": ep.path,
                "method": ep.method,
                "description": ep.description,
                "category": ep.category,
                "rpm_limit": ep.rpm_limit,
                "rph_limit": ep.rph_limit,
                "display_order": ep.display_order,
                "enabled": ep.enabled,
            }
            for ep in endpoints
        ]
    )


@router.post("/{repo_id}/endpoints", response_model=BaseResponse[dict])
async def create_endpoint(
    repo_id: str,
    endpoint_data: EndpointCreate,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    添加新的API端点

    Args:
        repo_id: 仓库ID或slug
        endpoint_data: 端点数据

    Returns:
        创建的端点信息
    """
    repo = await _get_repo_by_id(db, repo_id)
    if not repo:
        raise RepositoryNotFoundError()

    _check_repo_owner_permission(repo, current_user)

    endpoint = RepoEndpoint(
        repo_id=repo.id,
        path=endpoint_data.path,
        method=endpoint_data.method,
        description=endpoint_data.description,
        category=endpoint_data.category,
        rpm_limit=endpoint_data.rpm_limit,
        rph_limit=endpoint_data.rph_limit,
        display_order=endpoint_data.display_order,
        enabled=True,
    )

    db.add(endpoint)
    await db.commit()
    await db.refresh(endpoint)

    return BaseResponse(
        data={
            "id": str(endpoint.id),
            "path": endpoint.path,
            "method": endpoint.method,
            "description": endpoint.description,
            "category": endpoint.category,
            "rpm_limit": endpoint.rpm_limit,
            "rph_limit": endpoint.rph_limit,
            "display_order": endpoint.display_order,
            "enabled": endpoint.enabled,
        }
    )


@router.put("/{repo_id}/endpoints/{endpoint_id}", response_model=BaseResponse[dict])
async def update_endpoint(
    repo_id: str,
    endpoint_id: str,
    endpoint_data: EndpointUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    更新API端点

    Args:
        repo_id: 仓库ID或slug
        endpoint_id: 端点ID
        endpoint_data: 更新数据

    Returns:
        更新后的端点信息
    """
    repo = await _get_repo_by_id(db, repo_id)
    if not repo:
        raise RepositoryNotFoundError()

    _check_repo_owner_permission(repo, current_user)

    try:
        endpoint_uuid = UUID(endpoint_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的端点ID")

    result = await db.execute(
        select(RepoEndpoint).where(
            RepoEndpoint.id == endpoint_uuid,
            RepoEndpoint.repo_id == repo.id,
        )
    )
    endpoint = result.scalar_one_or_none()

    if not endpoint:
        raise HTTPException(status_code=404, detail="端点不存在")

    # 更新字段
    if endpoint_data.path is not None:
        endpoint.path = endpoint_data.path
    if endpoint_data.method is not None:
        endpoint.method = endpoint_data.method
    if endpoint_data.description is not None:
        endpoint.description = endpoint_data.description
    if endpoint_data.category is not None:
        endpoint.category = endpoint_data.category
    if endpoint_data.rpm_limit is not None:
        endpoint.rpm_limit = endpoint_data.rpm_limit
    if endpoint_data.rph_limit is not None:
        endpoint.rph_limit = endpoint_data.rph_limit
    if endpoint_data.display_order is not None:
        endpoint.display_order = endpoint_data.display_order
    if endpoint_data.enabled is not None:
        endpoint.enabled = endpoint_data.enabled

    await db.commit()
    await db.refresh(endpoint)

    return BaseResponse(
        data={
            "id": str(endpoint.id),
            "path": endpoint.path,
            "method": endpoint.method,
            "description": endpoint.description,
            "category": endpoint.category,
            "rpm_limit": endpoint.rpm_limit,
            "rph_limit": endpoint.rph_limit,
            "display_order": endpoint.display_order,
            "enabled": endpoint.enabled,
        }
    )


@router.delete("/{repo_id}/endpoints/{endpoint_id}", response_model=BaseResponse[dict])
async def delete_endpoint(
    repo_id: str,
    endpoint_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    删除API端点

    Args:
        repo_id: 仓库ID或slug
        endpoint_id: 端点ID

    Returns:
        删除结果
    """
    repo = await _get_repo_by_id(db, repo_id)
    if not repo:
        raise RepositoryNotFoundError()

    _check_repo_owner_permission(repo, current_user)

    try:
        endpoint_uuid = UUID(endpoint_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的端点ID")

    result = await db.execute(
        select(RepoEndpoint).where(
            RepoEndpoint.id == endpoint_uuid,
            RepoEndpoint.repo_id == repo.id,
        )
    )
    endpoint = result.scalar_one_or_none()

    if not endpoint:
        raise HTTPException(status_code=404, detail="端点不存在")

    await db.delete(endpoint)
    await db.commit()

    return BaseResponse(data={"message": "端点删除成功"})


@router.put("/{repo_id}/endpoints", response_model=BaseResponse[dict])
async def batch_update_endpoints(
    repo_id: str,
    data: EndpointsBatchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    批量更新API端点（替换模式）

    Args:
        repo_id: 仓库ID或slug
        data: 端点列表

    Returns:
        更新结果
    """
    repo = await _get_repo_by_id(db, repo_id)
    if not repo:
        raise RepositoryNotFoundError()

    _check_repo_owner_permission(repo, current_user)

    # 删除现有端点
    existing = await db.execute(
        select(RepoEndpoint).where(RepoEndpoint.repo_id == repo.id)
    )
    for ep in existing.scalars().all():
        await db.delete(ep)

    # 创建新端点
    new_endpoints = []
    for idx, ep_data in enumerate(data.endpoints):
        endpoint = RepoEndpoint(
            repo_id=repo.id,
            path=ep_data.path,
            method=ep_data.method,
            description=ep_data.description,
            category=ep_data.category,
            rpm_limit=ep_data.rpm_limit,
            rph_limit=ep_data.rph_limit,
            display_order=ep_data.display_order or idx,
            enabled=True,
        )
        db.add(endpoint)
        new_endpoints.append(endpoint)

    await db.commit()

    return BaseResponse(
        data={
            "message": f"成功更新 {len(new_endpoints)} 个端点",
            "count": len(new_endpoints),
        }
    )
