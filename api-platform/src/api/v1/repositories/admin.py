"""
仓库接口 —— 管理员仓库列表与审核（通过 / 驳回 / 上线 / 下线）

由 `scripts/dev/split_api_router.py` 从 `src/api/v1/repositories.py` 精确搬移生成，
函数体与原实现逐字一致（仅移动位置）。
"""

from typing import Optional
from fastapi import Depends, Query, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.config.database import get_db
from src.schemas.response import BaseResponse, RepositoryResponse, RepositoryListResponse, RepositoryOwnerResponse
from src.core.exceptions import RepositoryNotFoundError
from src.services.auth_service import get_current_user, check_admin_permission
from src.models.repository import Repository
from uuid import UUID
from src.schemas.request import RepositoryApproval, RepositoryReject

router = APIRouter()




# ==================== 管理员仓库审核接口 ====================
# 说明：管理员权限校验统一使用 src.services.auth_service.check_admin_permission，
#       不再在本模块重复定义（已在上方 import 引入）。


@router.get("/admin/all", response_model=BaseResponse[RepositoryListResponse])
async def list_all_repositories_for_admin(
    status: Optional[str] = Query(None, description="Status filter: pending/approved/rejected/online/offline"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    获取所有仓库（管理员专用）
    
    管理员可以查看所有仓库，支持按状态筛选。
    """
    from src.models.user import User
    
    # 检查管理员权限
    check_admin_permission(current_user)
    
    # 构建查询
    query = select(Repository)
    
    # 状态筛选
    if status:
        query = query.where(Repository.status == status)
    
    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页查询
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Repository.created_at.desc())
    result = await db.execute(query)
    repositories = result.scalars().all()
    
    # 构建响应
    items = []
    for repo in repositories:
        # 获取所有者信息
        owner_result = await db.execute(select(User).where(User.id == repo.owner_id))
        owner = owner_result.scalar_one_or_none()
        
        items.append(
            RepositoryResponse(
                id=str(repo.id),
                name=repo.name,
                slug=repo.slug,
                display_name=repo.display_name,
                description=repo.description,
                type=repo.repo_type,
                protocol=repo.protocol,
                status=repo.status,
                owner=RepositoryOwnerResponse(
                    id=str(repo.owner_id),
                    name=owner.email.split("@")[0] if owner else "未知",
                ),
                logo_url=repo.logo_url,
                created_at=repo.created_at,
                updated_at=repo.updated_at.isoformat() if repo.updated_at else None,
                online_at=repo.online_at.isoformat() if repo.online_at else None,
            )
        )
    
    return BaseResponse(
        data=RepositoryListResponse(
            items=items,
            pagination={
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            }
        )
    )


@router.post("/{repo_id}/approve", response_model=BaseResponse[RepositoryResponse])
async def approve_repository(
    repo_id: str,
    approval_data: RepositoryApproval,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    审核通过仓库（管理员专用）
    
    Args:
        repo_id: 仓库ID
        approval_data: 审核通过数据
    
    Returns:
        更新后的仓库信息
    """
    from src.models.user import User
    from datetime import datetime, timezone
    
    # 检查管理员权限
    check_admin_permission(current_user)
    
    # 查找仓库
    try:
        repo_uuid = UUID(repo_id) if len(repo_id) == 36 else None
    except ValueError:
        repo_uuid = None
    
    if repo_uuid:
        result = await db.execute(select(Repository).where(Repository.id == repo_uuid))
    else:
        result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    
    if not repo:
        raise RepositoryNotFoundError()
    
    # 检查状态是否允许审核
    if repo.status not in ['pending', 'rejected']:
        from src.core.exceptions import ValidationError
        raise ValidationError(f"仓库当前状态为 {repo.status}，无法审核")
    
    # 获取所有者信息
    owner_result = await db.execute(select(User).where(User.id == repo.owner_id))
    owner = owner_result.scalar_one_or_none()
    
    # 更新仓库状态
    repo.status = "approved"
    repo.approved_at = datetime.now(timezone.utc)
    repo.approved_by = current_user.id
    repo.reviewed_by = current_user.id
    
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
                id=str(repo.owner_id),
                name=owner.email.split("@")[0] if owner else "未知",
            ),
            logo_url=repo.logo_url,
            created_at=repo.created_at,
            updated_at=repo.updated_at.isoformat() if repo.updated_at else None,
        )
    )


@router.post("/{repo_id}/reject", response_model=BaseResponse[RepositoryResponse])
async def reject_repository(
    repo_id: str,
    reject_data: RepositoryReject,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    审核拒绝仓库（管理员专用）
    
    Args:
        repo_id: 仓库ID
        reject_data: 拒绝原因
    
    Returns:
        更新后的仓库信息
    """
    from src.models.user import User
    from datetime import datetime, timezone
    
    # 检查管理员权限
    check_admin_permission(current_user)
    
    # 查找仓库
    try:
        repo_uuid = UUID(repo_id) if len(repo_id) == 36 else None
    except ValueError:
        repo_uuid = None
    
    if repo_uuid:
        result = await db.execute(select(Repository).where(Repository.id == repo_uuid))
    else:
        result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    
    if not repo:
        raise RepositoryNotFoundError()
    
    # 检查状态是否允许审核
    if repo.status not in ['pending', 'approved']:
        from src.core.exceptions import ValidationError
        raise ValidationError(f"仓库当前状态为 {repo.status}，无法拒绝")
    
    # 获取所有者信息
    owner_result = await db.execute(select(User).where(User.id == repo.owner_id))
    owner = owner_result.scalar_one_or_none()
    
    # 更新仓库状态
    repo.status = "rejected"
    repo.reviewed_by = current_user.id
    
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
                id=str(repo.owner_id),
                name=owner.email.split("@")[0] if owner else "未知",
            ),
            logo_url=repo.logo_url,
            created_at=repo.created_at,
            updated_at=repo.updated_at.isoformat() if repo.updated_at else None,
        )
    )


@router.post("/{repo_id}/online", response_model=BaseResponse[RepositoryResponse])
async def online_repository(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    上线仓库（管理员专用）
    
    仓库必须先通过审核(approved)才能上线。
    
    Args:
        repo_id: 仓库ID
    
    Returns:
        更新后的仓库信息
    """
    from src.models.user import User
    from datetime import datetime, timezone
    
    # 检查管理员权限
    check_admin_permission(current_user)
    
    # 查找仓库
    try:
        repo_uuid = UUID(repo_id) if len(repo_id) == 36 else None
    except ValueError:
        repo_uuid = None
    
    if repo_uuid:
        result = await db.execute(select(Repository).where(Repository.id == repo_uuid))
    else:
        result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    
    if not repo:
        raise RepositoryNotFoundError()
    
    # 检查状态是否允许上线
    if repo.status not in ['approved', 'offline']:
        from src.core.exceptions import ValidationError
        raise ValidationError(f"仓库当前状态为 {repo.status}，必须先审核通过才能上线")
    
    # 获取所有者信息
    owner_result = await db.execute(select(User).where(User.id == repo.owner_id))
    owner = owner_result.scalar_one_or_none()
    
    # 更新仓库状态
    repo.status = "online"
    repo.online_at = datetime.now(timezone.utc)
    
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
                id=str(repo.owner_id),
                name=owner.email.split("@")[0] if owner else "未知",
            ),
            logo_url=repo.logo_url,
            created_at=repo.created_at,
            updated_at=repo.updated_at.isoformat() if repo.updated_at else None,
            online_at=repo.online_at.isoformat() if repo.online_at else None,
        )
    )


@router.post("/{repo_id}/offline", response_model=BaseResponse[RepositoryResponse])
async def offline_repository(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    下线仓库（管理员专用）
    
    Args:
        repo_id: 仓库ID
    
    Returns:
        更新后的仓库信息
    """
    from src.models.user import User
    from datetime import datetime, timezone
    
    # 检查管理员权限
    check_admin_permission(current_user)
    
    # 查找仓库
    try:
        repo_uuid = UUID(repo_id) if len(repo_id) == 36 else None
    except ValueError:
        repo_uuid = None
    
    if repo_uuid:
        result = await db.execute(select(Repository).where(Repository.id == repo_uuid))
    else:
        result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    
    if not repo:
        raise RepositoryNotFoundError()
    
    # 检查状态
    if repo.status != "online":
        from src.core.exceptions import ValidationError
        raise ValidationError(f"仓库当前状态为 {repo.status}，只能下线已上线的仓库")
    
    # 获取所有者信息
    owner_result = await db.execute(select(User).where(User.id == repo.owner_id))
    owner = owner_result.scalar_one_or_none()
    
    # 更新仓库状态
    repo.status = "offline"
    repo.offline_at = datetime.now(timezone.utc)
    
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
                id=str(repo.owner_id),
                name=owner.email.split("@")[0] if owner else "未知",
            ),
            logo_url=repo.logo_url,
            created_at=repo.created_at,
            updated_at=repo.updated_at.isoformat() if repo.updated_at else None,
        )
    )
