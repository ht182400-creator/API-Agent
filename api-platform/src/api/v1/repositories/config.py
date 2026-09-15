"""
仓库接口 —— 仓库配置更新（端点 + 限流 + 定价一次性提交）

由 `scripts/dev/split_api_router.py` 从 `src/api/v1/repositories.py` 精确搬移生成，
函数体与原实现逐字一致（仅移动位置）。
"""

from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.config.database import get_db
from src.schemas.response import BaseResponse, RepositoryResponse, RepositoryOwnerResponse, RepositoryPricingResponse, RepositoryLimitsResponse, RepositoryEndpointResponse
from src.core.exceptions import RepositoryNotFoundError
from src.services.auth_service import get_current_user
from src.models.repository import RepoEndpoint, RepoLimits, RepoPricing
from src.schemas.request import RepositoryConfigUpdate
from src.api.v1.repositories._shared import _validate_endpoint_url, _check_repo_owner_permission, _get_repo_by_id

router = APIRouter()




# ==================== 仓库完整配置更新 API ====================

@router.put("/{repo_id}/config", response_model=BaseResponse[RepositoryResponse])
async def update_repository_config(
    repo_id: str,
    config_data: RepositoryConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),  # noqa: F821
):
    """
    更新仓库的完整配置（基本信息 + 端点 + 限流）

    Args:
        repo_id: 仓库ID或slug
        config_data: 完整配置数据

    Returns:
        更新后的仓库信息
    """
    from src.models.user import User
    from datetime import datetime, timezone

    repo = await _get_repo_by_id(db, repo_id)
    if not repo:
        raise RepositoryNotFoundError()

    _check_repo_owner_permission(repo, current_user)

    # 更新基本信息
    if config_data.display_name is not None:
        repo.display_name = config_data.display_name
    if config_data.description is not None:
        repo.description = config_data.description
    if config_data.endpoint_url is not None:
        # 【N-1】写入侧 SSRF 校验
        repo.endpoint_url = _validate_endpoint_url(config_data.endpoint_url)
    if config_data.repo_type is not None:
        repo.repo_type = config_data.repo_type

    # 更新端点配置
    if config_data.endpoints is not None:
        # 删除现有端点
        existing = await db.execute(
            select(RepoEndpoint).where(RepoEndpoint.repo_id == repo.id)
        )
        for ep in existing.scalars().all():
            await db.delete(ep)

        # 创建新端点
        for idx, ep_data in enumerate(config_data.endpoints):
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

    # 更新限流配置
    if config_data.limits is not None:
        result = await db.execute(
            select(RepoLimits).where(RepoLimits.repo_id == repo.id)
        )
        limits = result.scalar_one_or_none()

        if not limits:
            limits = RepoLimits(repo_id=repo.id)
            db.add(limits)

        if config_data.limits.rpm is not None:
            limits.rpm = config_data.limits.rpm
        if config_data.limits.rph is not None:
            limits.rph = config_data.limits.rph
        if config_data.limits.rpd is not None:
            limits.rpd = config_data.limits.rpd
        if config_data.limits.burst_limit is not None:
            limits.burst_limit = config_data.limits.burst_limit
        if config_data.limits.concurrent_limit is not None:
            limits.concurrent_limit = config_data.limits.concurrent_limit
        if config_data.limits.request_timeout is not None:
            limits.request_timeout = config_data.limits.request_timeout
        if config_data.limits.connect_timeout is not None:
            limits.connect_timeout = config_data.limits.connect_timeout

    # 更新定价配置
    if config_data.pricing_type is not None:
        result = await db.execute(
            select(RepoPricing).where(RepoPricing.repo_id == repo.id)
        )
        pricing = result.scalar_one_or_none()

        if not pricing:
            pricing = RepoPricing(repo_id=repo.id, pricing_type=config_data.pricing_type)
            db.add(pricing)

        pricing.pricing_type = config_data.pricing_type
        if config_data.price_per_call is not None:
            pricing.price_per_call = str(config_data.price_per_call)
        if config_data.price_per_token is not None:
            pricing.price_per_token = str(config_data.price_per_token)
        if config_data.monthly_price is not None:
            pricing.monthly_price = str(config_data.monthly_price)
        if config_data.yearly_price is not None:
            pricing.yearly_price = str(config_data.yearly_price)
        if config_data.free_calls is not None:
            pricing.free_calls = config_data.free_calls
        if config_data.free_tokens is not None:
            pricing.free_tokens = config_data.free_tokens
        if config_data.free_quota_days is not None:
            pricing.free_quota_days = config_data.free_quota_days

    repo.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(repo)

    # 获取完整信息构建响应
    owner_result = await db.execute(select(User).where(User.id == repo.owner_id))
    owner = owner_result.scalar_one_or_none()

    # 获取端点
    endpoints_result = await db.execute(
        select(RepoEndpoint).where(
            RepoEndpoint.repo_id == repo.id,
            RepoEndpoint.enabled == True
        ).order_by(RepoEndpoint.display_order)
    )
    endpoints_list = endpoints_result.scalars().all()

    # 获取限流配置
    limits_result = await db.execute(
        select(RepoLimits).where(RepoLimits.repo_id == repo.id)
    )
    limits_data = limits_result.scalar_one_or_none()

    # 获取定价配置
    pricing_result = await db.execute(
        select(RepoPricing).where(RepoPricing.repo_id == repo.id)
    )
    pricing = pricing_result.scalar_one_or_none()

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
            endpoint=repo.endpoint_url,
            owner=RepositoryOwnerResponse(
                id=str(repo.owner_id),
                name=owner.email.split("@")[0] if owner else "未知",
            ),
            pricing=RepositoryPricingResponse(
                type=pricing.pricing_type if pricing else "free",
                price_per_call=float(pricing.price_per_call) if pricing and pricing.price_per_call else None,
                price_per_token=float(pricing.price_per_token) if pricing and pricing.price_per_token else None,
                monthly_price=float(pricing.monthly_price) if pricing and pricing.monthly_price else None,
                free_calls=pricing.free_calls if pricing else 0,
            ) if pricing else None,
            limits=RepositoryLimitsResponse(
                rpm=limits_data.rpm if limits_data else 1000,
                rph=limits_data.rph if limits_data else 10000,
                daily=limits_data.rpd if limits_data else 100000,
            ),
            endpoints=[
                RepositoryEndpointResponse(
                    path=ep.path,
                    method=ep.method,
                    description=ep.description,
                )
                for ep in endpoints_list
            ],
            logo_url=repo.logo_url,
            created_at=repo.created_at,
            updated_at=repo.updated_at.isoformat() if repo.updated_at else None,
        )
    )
