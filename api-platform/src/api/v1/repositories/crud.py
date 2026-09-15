"""
仓库接口 —— 仓库创建 / 更新 / 删除

由 `scripts/dev/split_api_router.py` 从 `src/api/v1/repositories.py` 精确搬移生成，
函数体与原实现逐字一致（仅移动位置）。
"""

from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.config.database import get_db
from src.schemas.response import BaseResponse, RepositoryResponse, RepositoryOwnerResponse
from src.core.exceptions import RepositoryNotFoundError, AuthorizationError
from src.services.auth_service import get_current_user
from src.models.repository import Repository
from uuid import uuid4, UUID
from src.schemas.request import RepositoryCreate, RepositoryUpdate
from src.api.v1.repositories._shared import _validate_endpoint_url

router = APIRouter()




@router.post("", response_model=BaseResponse[RepositoryResponse])
async def create_repository(
    repo_data: RepositoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    Create a new repository (仓库所有者创建仓库)
    
    Args:
        repo_data: Repository creation data
    
    Returns:
        Created repository
    """
    from src.models.user import User
    from src.services.permission_service import PermissionService
    
    # 【V4.0 重构】使用统一的权限检查
    # 可以创建仓库的角色: developer, admin, super_admin
    if not PermissionService.can_create_repo(current_user):
        raise AuthorizationError("只有开发者、管理员或超级管理员可以创建仓库")
    
    # 生成 slug
    slug = repo_data.name.lower().replace("_", "-").replace(" ", "-")
    # 确保 slug 唯一
    existing = await db.execute(
        select(Repository).where(Repository.slug == slug)
    )
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid4().hex[:8]}"
    
    # 【V4.2 修改】根据用户类型设置初始状态
    # 管理员和超级管理员创建的仓库直接上线，其他用户需要审核
    if current_user.user_type in ['admin', 'super_admin']:
        initial_status = "online"  # 管理员创建的直接上线
    else:
        initial_status = "pending"  # 其他用户需要审核
    
    # 创建仓库
    repo = Repository(
        name=repo_data.name,
        slug=slug,
        display_name=repo_data.display_name or repo_data.name,
        description=repo_data.description,
        repo_type=repo_data.repo_type,
        protocol=repo_data.protocol or "http",
        status=initial_status,
        owner_id=current_user.id,
        owner_type="external",  # 外部用户创建
        logo_url=repo_data.logo_url,  # V5.0 自定义图标
        # 【N-1】写入侧校验后端地址（原先该字段被接收但未落库，属缺陷一并修复）
        endpoint_url=_validate_endpoint_url(repo_data.endpoint_url),
    )
    
    db.add(repo)
    await db.commit()
    await db.refresh(repo)
    
    return BaseResponse(
        data=RepositoryResponse(
            id=str(repo.id),
            name=repo.name,
            slug=repo.slug,
            display_name=repo.display_name,
            description=repo.description,
            type=repo.repo_type,
            protocol=repo.protocol,
            status=repo.status,
            owner=RepositoryOwnerResponse(
                id=str(current_user.id),
                name=current_user.email.split("@")[0],
            ),
            logo_url=repo.logo_url,
            created_at=repo.created_at,
        )
    )


@router.put("/{repo_id}", response_model=BaseResponse[RepositoryResponse])
async def update_repository(
    repo_id: str,
    repo_data: RepositoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    Update a repository (仓库所有者更新仓库)
    
    Args:
        repo_id: Repository ID
        repo_data: Repository update data
    
    Returns:
        Updated repository
    """
    from src.models.user import User
    from uuid import UUID
    
    # 查找仓库 - 处理 UUID 和字符串 ID
    try:
        repo_uuid = UUID(repo_id) if len(repo_id) == 36 else None
    except ValueError:
        repo_uuid = None
    
    if repo_uuid:
        result = await db.execute(
            select(Repository).where(Repository.id == repo_uuid)
        )
    else:
        result = await db.execute(
            select(Repository).where(Repository.id == repo_id)
        )
    repo = result.scalar_one_or_none()
    
    if not repo:
        raise RepositoryNotFoundError()
    
    # 【V4.0 重构】使用统一的权限检查
    from src.services.permission_service import PermissionService
    # 检查权限（必须是仓库所有者或超级管理员）
    if repo.owner_id != current_user.id and not PermissionService.is_super_admin(current_user):
        raise AuthorizationError("无权修改此仓库")
    
    # 权限检查：只有管理员可以修改状态
    if repo_data.status is not None and repo.owner_id == current_user.id:
        from src.core.exceptions import AuthorizationError
        raise AuthorizationError("状态变更需要管理员审核，请联系管理员操作")
    
    # 更新字段
    if repo_data.display_name is not None:
        repo.display_name = repo_data.display_name
    if repo_data.description is not None:
        repo.description = repo_data.description
    if repo_data.repo_type is not None:
        repo.repo_type = repo_data.repo_type
    if repo_data.endpoint_url is not None:
        # 【N-1】写入侧 SSRF 校验
        repo.endpoint_url = _validate_endpoint_url(repo_data.endpoint_url)
    if repo_data.status is not None:
        repo.status = repo_data.status
        if repo_data.status == "online" and not repo.online_at:
            from datetime import datetime, timezone
            repo.online_at = datetime.now(timezone.utc)
    # V5.0 自定义图标
    if repo_data.logo_url is not None:
        repo.logo_url = repo_data.logo_url
    
    await db.commit()
    await db.refresh(repo)
    
    return BaseResponse(
        data=RepositoryResponse(
            id=str(repo.id),
            name=repo.name,
            slug=repo.slug,
            display_name=repo.display_name,
            description=repo.description,
            type=repo.repo_type,
            protocol=repo.protocol,
            status=repo.status,
            owner=RepositoryOwnerResponse(
                id=str(current_user.id),
                name=current_user.email.split("@")[0],
            ),
            logo_url=repo.logo_url,
            created_at=repo.created_at,
        )
    )


@router.delete("/{repo_id}", response_model=BaseResponse[dict])
async def delete_repository(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    Delete a repository (仓库所有者删除仓库)
    
    Args:
        repo_id: Repository ID
    
    Returns:
        Success message
    """
    # 查找仓库
    try:
        repo_uuid = UUID(repo_id) if len(repo_id) == 36 else None
    except ValueError:
        repo_uuid = None
    
    if repo_uuid:
        result = await db.execute(
            select(Repository).where(Repository.id == repo_uuid)
        )
    else:
        result = await db.execute(
            select(Repository).where(Repository.id == repo_id)
        )
    repo = result.scalar_one_or_none()
    
    if not repo:
        raise RepositoryNotFoundError()
    
    # 【V4.0 重构】使用统一的权限检查
    from src.services.permission_service import PermissionService
    # 检查权限（必须是仓库所有者或管理员/超级管理员）
    if repo.owner_id != current_user.id and not PermissionService.is_admin(current_user):
        raise AuthorizationError("无权删除此仓库")
    
    await db.delete(repo)
    await db.commit()
    
    return BaseResponse(data={"message": "仓库删除成功"})
