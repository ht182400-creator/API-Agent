"""Repository API - 仓库接口"""

from typing import Optional, List

from fastapi import APIRouter, Depends, Query, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.config.database import get_db
from src.schemas.response import (
    BaseResponse,
    RepositoryResponse,
    RepositoryListResponse,
    RepositoryOwnerResponse,
    RepositoryPricingResponse,
    RepositoryLimitsResponse,
    RepositoryEndpointResponse,
    RepositorySLAResponse,
)
from src.core.exceptions import RepositoryNotFoundError, RateLimitError

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
    
    # Get pricing for each repository
    items = []
    for repo in repositories:
        pricing_result = await db.execute(
            select(RepoPricing).where(RepoPricing.repo_id == repo.id)
        )
        pricing = pricing_result.scalar_one_or_none()
        
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
        
        # Build endpoints
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
                endpoints=endpoints,
                docs_url=repo.api_docs_url,
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


@router.get("/{repo_slug}", response_model=BaseResponse[RepositoryResponse])
async def get_repository(
    repo_slug: str,
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
    
    endpoints = [
        RepositoryEndpointResponse(
            path="/chat",
            method="POST",
            description="智能问答",
        ),
    ]
    
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
            limits=RepositoryLimitsResponse(
                rpm=repo.rate_limit_rpm if hasattr(repo, 'rate_limit_rpm') else 1000,
                rph=10000,
                daily=100000,
            ),
            endpoints=endpoints,
            docs_url=repo.api_docs_url,
            sla=RepositorySLAResponse(
                uptime=float(repo.sla_uptime) if repo.sla_uptime else None,
                latency_p99=repo.sla_latency_p99,
            ),
            created_at=repo.created_at,
            online_at=repo.online_at,
        )
    )


@router.post("/{repo_slug}/chat", response_model=BaseResponse[dict])
async def chat(
    repo_slug: str,
    request_data: dict,
    request: Request,
    x_access_key: str = Header(..., description="API Access Key"),
    x_signature: str = Header(..., description="HMAC Signature"),
    x_timestamp: str = Header(..., description="Request timestamp"),
    x_nonce: str = Header(..., description="Request nonce"),
    db: AsyncSession = Depends(get_db),
):
    """
    Call repository chat API
    
    This endpoint proxies requests to the underlying repository's chat API.
    
    Args:
        repo_slug: Repository slug
        request_data: Chat request data
    
    Returns:
        Chat response
    """
    # In production, this would:
    # 1. Verify the API key
    # 2. Check rate limits
    # 3. Forward request to repository adapter
    # 4. Process response and return
    
    # Placeholder response
    return BaseResponse(
        data={
            "answer": "这是一个模拟的回答。在生产环境中，这将调用实际的心理问答API服务。",
            "suggestions": [
                "建议您保持规律的作息时间",
                "可以尝试冥想放松",
                "建议咨询专业心理医生",
            ],
            "request_id": getattr(request.state, "request_id", "mock-request-id"),
        }
    )


@router.post("/{repo_slug}/translate", response_model=BaseResponse[dict])
async def translate(
    repo_slug: str,
    request_data: dict,
    request: Request,
    x_access_key: str = Header(...),
    x_signature: str = Header(...),
    x_timestamp: str = Header(...),
    x_nonce: str = Header(...),
):
    """
    Call repository translation API
    
    Args:
        repo_slug: Repository slug
        request_data: Translation request data
    
    Returns:
        Translation response
    """
    return BaseResponse(
        data={
            "result": "这是模拟的翻译结果。",
            "detected_lang": "en",
            "request_id": getattr(request.state, "request_id", "mock-request-id"),
        }
    )


@router.post("/{repo_slug}/recognize", response_model=BaseResponse[dict])
async def recognize(
    repo_slug: str,
    request_data: dict,
    request: Request,
    x_access_key: str = Header(...),
    x_signature: str = Header(...),
    x_timestamp: str = Header(...),
    x_nonce: str = Header(...),
):
    """
    Call repository OCR/recognition API
    
    Args:
        repo_slug: Repository slug
        request_data: Recognition request data
    
    Returns:
        Recognition response
    """
    return BaseResponse(
        data={
            "text": "这是模拟的OCR识别结果。",
            "confidence": 0.95,
            "request_id": getattr(request.state, "request_id", "mock-request-id"),
        }
    )
