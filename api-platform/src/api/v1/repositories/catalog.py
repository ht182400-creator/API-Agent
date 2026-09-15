"""
仓库接口 —— 仓库列表与详情

由 `scripts/dev/split_api_router.py` 从 `src/api/v1/repositories.py` 精确搬移生成，
函数体与原实现逐字一致（仅移动位置）。
"""

from typing import Optional
from fastapi import Depends, Query, Request, HTTPException, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.config.database import get_db
from src.schemas.response import BaseResponse, RepositoryResponse, RepositoryListResponse, RepositoryOwnerResponse, RepositoryPricingResponse, RepositoryLimitsResponse, RepositoryEndpointResponse, RepositorySLAResponse
from src.core.exceptions import RepositoryNotFoundError, AuthorizationError
from src.services.auth_service import get_current_user
from src.models.repository import Repository, RepoEndpoint, RepoLimits, RepoPricing
from uuid import UUID

router = APIRouter()




@router.get("", response_model=BaseResponse[RepositoryListResponse])
async def list_repositories(
    type: Optional[str] = Query(None, description="Repository type filter"),
    protocol: Optional[str] = Query(None, description="Protocol type filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of available repositories
    
    Returns paginated list of repositories that are online and approved.
    """
    from src.models.repository import Repository, RepoPricing
    
    # Build query
    query = select(Repository).where(Repository.status == "online")
    
    if type:
        query = query.where(Repository.repo_type == type)
    if protocol:
        query = query.where(Repository.protocol == protocol)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    repositories = result.scalars().all()
    
    # Get pricing, endpoints, and limits for each repository
    items = []
    for repo in repositories:
        # Get pricing
        pricing_result = await db.execute(
            select(RepoPricing).where(RepoPricing.repo_id == repo.id)
        )
        pricing = pricing_result.scalar_one_or_none()
        
        # Get endpoints from database
        endpoints_result = await db.execute(
            select(RepoEndpoint).where(
                RepoEndpoint.repo_id == repo.id,
                RepoEndpoint.enabled == True
            ).order_by(RepoEndpoint.display_order)
        )
        endpoints_list = endpoints_result.scalars().all()
        
        # Get limits from database
        limits_result = await db.execute(
            select(RepoLimits).where(RepoLimits.repo_id == repo.id)
        )
        limits_data = limits_result.scalar_one_or_none()
        
        # Get owner info
        owner_response = RepositoryOwnerResponse(
            id=str(repo.owner_id),
            name="平台官方" if repo.owner_type == "internal" else "仓库所有者"
        )
        
        # Build pricing response
        pricing_response = None
        if pricing:
            pricing_response = RepositoryPricingResponse(
                type=pricing.pricing_type,
                price_per_call=float(pricing.price_per_call) if pricing.price_per_call else None,
                price_per_token=float(pricing.price_per_token) if pricing.price_per_token else None,
                monthly_price=float(pricing.monthly_price) if pricing.monthly_price else None,
                free_calls=pricing.free_calls,
                free_tokens=pricing.free_tokens,
            )
        
        # Build endpoints from database, fallback to default if none
        if endpoints_list:
            endpoints = [
                RepositoryEndpointResponse(
                    path=ep.path,
                    method=ep.method,
                    description=ep.description,
                )
                for ep in endpoints_list
            ]
        else:
            endpoints = [
                RepositoryEndpointResponse(
                    path="/chat",
                    method="POST",
                    description="智能问答",
                ),
                RepositoryEndpointResponse(
                    path="/assess",
                    method="POST",
                    description="心理评估",
                ),
            ]
        
        # Build limits from database, fallback to default if none
        limits_response = None
        if limits_data:
            limits_response = RepositoryLimitsResponse(
                rpm=limits_data.rpm or 1000,
                rph=limits_data.rph or 10000,
                daily=limits_data.rpd or 100000,
            )
        else:
            limits_response = RepositoryLimitsResponse(
                rpm=1000,
                rph=10000,
                daily=100000,
            )
        
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
                owner=owner_response,
                pricing=pricing_response,
                limits=limits_response,
                endpoints=endpoints,
                docs_url=repo.api_docs_url,
                sla=RepositorySLAResponse(
                    uptime=float(repo.sla_uptime.replace('%', '')) if repo.sla_uptime else None,
                    latency_p99=repo.sla_latency_p99,
                ),
                logo_url=repo.logo_url,
                created_at=repo.created_at,
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


@router.get("/my", response_model=BaseResponse[RepositoryListResponse])
async def list_my_repositories(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),
):
    """
    Get current user's repositories (仓库所有者查看自己创建的仓库)
    
    Returns paginated list of repositories owned by the current user.
    """
    from src.models.repository import Repository, RepoPricing
    
    # 查询当前用户创建的仓库
    query = select(Repository).where(Repository.owner_id == current_user.id)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Repository.created_at.desc())
    result = await db.execute(query)
    repositories = result.scalars().all()
    
    # Get pricing, endpoints, and limits for each repository
    items = []
    for repo in repositories:
        # Get pricing
        pricing_result = await db.execute(
            select(RepoPricing).where(RepoPricing.repo_id == repo.id)
        )
        pricing = pricing_result.scalar_one_or_none()
        
        # Get endpoints from database
        endpoints_result = await db.execute(
            select(RepoEndpoint).where(
                RepoEndpoint.repo_id == repo.id,
                RepoEndpoint.enabled == True
            ).order_by(RepoEndpoint.display_order)
        )
        endpoints_list = endpoints_result.scalars().all()
        
        # Get limits from database
        limits_result = await db.execute(
            select(RepoLimits).where(RepoLimits.repo_id == repo.id)
        )
        limits_data = limits_result.scalar_one_or_none()
        
        owner_response = RepositoryOwnerResponse(
            id=str(current_user.id),
            name=current_user.email.split("@")[0],
        )
        
        pricing_response = None
        if pricing:
            pricing_response = RepositoryPricingResponse(
                type=pricing.pricing_type,
                price_per_call=float(pricing.price_per_call) if pricing.price_per_call else None,
                price_per_token=float(pricing.price_per_token) if pricing.price_per_token else None,
                monthly_price=float(pricing.monthly_price) if pricing.monthly_price else None,
                free_calls=pricing.free_calls,
            )
        
        # Build endpoints from database
        endpoints_response = [
            RepositoryEndpointResponse(
                path=ep.path,
                method=ep.method,
                description=ep.description,
            )
            for ep in endpoints_list
        ]
        
        # Build limits from database
        limits_response = None
        if limits_data:
            limits_response = RepositoryLimitsResponse(
                rpm=limits_data.rpm or 1000,
                rph=limits_data.rph or 10000,
                daily=limits_data.rpd or 100000,
            )
        
        repo_data = {
            "id": str(repo.id),
            "name": repo.name,
            "slug": repo.slug,
            "display_name": repo.display_name,
            "description": repo.description,
            "type": repo.repo_type,
            "category": repo.repo_type,
            "owner": owner_response,
            "protocol": repo.protocol,
            "status": repo.status,
            "pricing": pricing_response,
            "limits": limits_response,
            "endpoints": endpoints_response,
            "docs_url": repo.api_docs_url,
            "sla": RepositorySLAResponse(
                uptime=float(repo.sla_uptime.replace('%', '')) if repo.sla_uptime else None,
                latency_p99=repo.sla_latency_p99,
            ),
            "logo_url": repo.logo_url,
            "created_at": repo.created_at.isoformat() if repo.created_at else None,
            "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
        }
        items.append(repo_data)
    
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


@router.get("/{repo_id}/stats", response_model=BaseResponse[dict])
async def get_repository_stats(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    Get repository statistics (仓库所有者查看统计)
    
    Args:
        repo_id: Repository ID
    
    Returns:
        Repository statistics
    """
    from src.models.user import User
    from datetime import datetime, timedelta, timezone
    
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
    # 检查权限: 仓库所有者本人或管理员可以查看
    if repo.owner_id != current_user.id and not PermissionService.is_admin(current_user):
        raise AuthorizationError("无权查看此仓库统计")


@router.get("/{repo_slug}", response_model=BaseResponse[RepositoryResponse])
async def get_repository(
    repo_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Get repository details by slug
    
    Args:
        repo_slug: Repository URL-friendly name
    
    Returns:
        Repository details
    """
    from src.models.repository import Repository, RepoPricing
    from src.models.user import User
    
    # 防止 /{repo_slug} 路由错误匹配带有额外路径的请求
    # 如 /repositories/weather-api/current 应该匹配 proxy 路由，而不是这个路由
    if "/" in repo_slug:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Find repository
    result = await db.execute(
        select(Repository).where(Repository.slug == repo_slug)
    )
    repo = result.scalar_one_or_none()
    
    if not repo:
        raise RepositoryNotFoundError()
    
    # Get owner
    owner_result = await db.execute(
        select(User).where(User.id == repo.owner_id)
    )
    owner = owner_result.scalar_one_or_none()
    
    # Get pricing
    pricing_result = await db.execute(
        select(RepoPricing).where(RepoPricing.repo_id == repo.id)
    )
    pricing = pricing_result.scalar_one_or_none()
    
    # Get endpoints from database
    endpoints_result = await db.execute(
        select(RepoEndpoint).where(
            RepoEndpoint.repo_id == repo.id,
            RepoEndpoint.enabled == True
        ).order_by(RepoEndpoint.display_order)
    )
    endpoints_list = endpoints_result.scalars().all()
    
    # Get limits from database
    limits_result = await db.execute(
        select(RepoLimits).where(RepoLimits.repo_id == repo.id)
    )
    limits_data = limits_result.scalar_one_or_none()
    
    # Build response
    owner_response = None
    if owner:
        owner_response = RepositoryOwnerResponse(
            id=str(owner.id),
            name=owner.email.split("@")[0],
        )
    
    pricing_response = None
    if pricing:
        pricing_response = RepositoryPricingResponse(
            type=pricing.pricing_type,
            price_per_call=float(pricing.price_per_call) if pricing.price_per_call else None,
            price_per_token=float(pricing.price_per_token) if pricing.price_per_token else None,
            monthly_price=float(pricing.monthly_price) if pricing.monthly_price else None,
            free_calls=pricing.free_calls,
            free_tokens=pricing.free_tokens,
        )
    
    # Build endpoints from database, fallback to default if none
    if endpoints_list:
        endpoints = [
            RepositoryEndpointResponse(
                path=ep.path,
                method=ep.method,
                description=ep.description,
            )
            for ep in endpoints_list
        ]
    else:
        endpoints = [
            RepositoryEndpointResponse(
                path="/chat",
                method="POST",
                description="智能问答",
            ),
        ]
    
    # Build limits from database, fallback to default if none
    if limits_data:
        limits_response = RepositoryLimitsResponse(
            rpm=limits_data.rpm or 1000,
            rph=limits_data.rph or 10000,
            daily=limits_data.rpd or 100000,
        )
    else:
        limits_response = RepositoryLimitsResponse(
            rpm=1000,
            rph=10000,
            daily=100000,
        )
    
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
            owner=owner_response,
            pricing=pricing_response,
            limits=limits_response,
            endpoints=endpoints,
            docs_url=repo.api_docs_url,
            sla=RepositorySLAResponse(
                uptime=float(repo.sla_uptime.replace('%', '')) if repo.sla_uptime else None,
                latency_p99=repo.sla_latency_p99,
            ),
            logo_url=repo.logo_url,
            created_at=repo.created_at,
            online_at=repo.online_at,
        )
    )
