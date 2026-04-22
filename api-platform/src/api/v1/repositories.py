"""Repository API - 仓库接口"""

from typing import Optional, List

from fastapi import APIRouter, Depends, Query, Request, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, Numeric

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
from src.core.exceptions import RepositoryNotFoundError, RateLimitError, AuthorizationError
from src.services.auth_service import get_current_user
from src.models.repository import Repository, RepoEndpoint, RepoLimits, RepoPricing
from src.schemas.request import (
    EndpointCreate,
    EndpointUpdate,
    EndpointsBatchUpdate,
    LimitsUpdate,
    RepositoryConfigUpdate,
)
from uuid import uuid4, UUID

router = APIRouter()


# ==================== 计费辅助函数 ====================

async def calculate_and_charge(
    db: AsyncSession,
    user_id: UUID,
    repo_id: UUID,
    api_key_id: UUID,
    tokens_used: int = 0,
) -> tuple:
    """
    计算并扣除API调用费用
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        repo_id: 仓库ID
        api_key_id: API Key ID
        tokens_used: 使用的Token数量
    
    Returns:
        (cost, description) - 费用和描述
    """
    from decimal import Decimal
    from src.models.billing import Account, Bill, APICallLog
    from src.models.repository import RepoPricing
    from src.config.settings import settings
    import random
    
    # 获取仓库定价信息
    pricing_result = await db.execute(
        select(RepoPricing).where(RepoPricing.repo_id == repo_id)
    )
    pricing = pricing_result.scalar_one_or_none()
    
    # 计算费用
    cost = Decimal("0")
    description = "API调用"
    
    # 优先使用仓库的 RepoPricing 配置
    if pricing and pricing.pricing_type:
        if pricing.pricing_type == "free":
            # 免费
            cost = Decimal("0")
            description = "免费调用"
        elif pricing.pricing_type in ("per_call", "subscription") and pricing.price_per_call:
            # 按次计费
            cost = Decimal(str(pricing.price_per_call))
            description = f"{pricing.pricing_type}计费-按次"
        elif pricing.pricing_type == "token" and pricing.price_per_token:
            # 按Token计费
            if tokens_used > 0:
                cost = Decimal(str(pricing.price_per_token)) * tokens_used
                description = f"token计费-按Token({tokens_used} tokens)"
            else:
                cost = Decimal("0")
                description = "token计费-无Token消耗"
        else:
            # 仓库配置了定价类型但没有价格，使用默认值
            cost = Decimal(str(settings.billing_default_price_per_call))
            description = f"默认计费(仓库未配置价格)"
    elif settings.billing_default_enabled:
        # 使用全局默认配置
        if settings.billing_default_type == "free":
            cost = Decimal("0")
            description = "免费调用(全局默认)"
        elif settings.billing_default_type == "per_call":
            cost = Decimal(str(settings.billing_default_price_per_call))
            description = f"按次计费(默认 ¥{settings.billing_default_price_per_call})"
        elif settings.billing_default_type == "token" and tokens_used > 0:
            cost = Decimal(str(settings.billing_default_price_per_token)) * tokens_used
            description = f"按Token计费(默认 ¥{settings.billing_default_price_per_token}/token)"
        else:
            cost = Decimal("0")
            description = "不计费"
    else:
        # 计费未启用
        cost = Decimal("0")
        description = "不计费(计费已禁用)"
    
    if cost <= 0:
        return Decimal("0"), description
    
    # 获取用户账户
    account_result = await db.execute(
        select(Account).where(
            Account.user_id == user_id,
            Account.account_type == "balance"
        )
    )
    account = account_result.scalar_one_or_none()
    
    if not account:
        # 没有账户，不扣费
        return cost, description
    
    # 检查余额是否足够
    balance = Decimal(str(account.balance))
    if balance < cost:
        # 余额不足，不扣费（但仍记录调用）
        return cost, description
    
    # 扣费
    balance_before = balance
    balance_after = balance - cost
    account.balance = str(balance_after)
    account.total_consume = str(Decimal(str(account.total_consume)) + cost)
    
    # 获取环境标识
    environment = "simulation" if settings.payment_mock_mode else "production"
    
    # 生成账单号
    import time
    bill_no = f"BILL{int(time.time() * 1000)}"
    
    # 创建消费账单
    bill = Bill(
        user_id=user_id,
        bill_no=bill_no,
        bill_type="consume",  # 与查询端保持一致
        amount=str(-cost),  # 负数表示消费
        balance_before=str(balance_before),
        balance_after=str(balance_after),
        source_type="api_call",
        source_id=str(api_key_id),
        environment=environment,
        description=f"{description} - 仓库:{str(repo_id)[:8]}",
        status="completed",
    )
    db.add(bill)
    
    return cost, description


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
    from datetime import datetime, timedelta
    
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
    
    # 检查权限
    if repo.owner_id != current_user.id and current_user.user_type not in ['super_admin', 'admin']:
        raise AuthorizationError("无权查看此仓库统计")
    
    # 从数据库查询真实统计数据
    from src.models.billing import APICallLog
    
    # 统一使用北京时间，与日志记录时间保持一致
    now = datetime.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    
    # 今日调用量
    today_result = await db.execute(
        select(func.count(APICallLog.id)).where(
            and_(
                APICallLog.repo_id == repo.id,
                func.date(APICallLog.created_at) == today,
            )
        )
    )
    today_calls = today_result.scalar() or 0
    
    # 本周调用量
    week_result = await db.execute(
        select(func.count(APICallLog.id)).where(
            and_(
                APICallLog.repo_id == repo.id,
                APICallLog.created_at >= week_ago,
            )
        )
    )
    week_calls = week_result.scalar() or 0
    
    # 总调用量
    total_result = await db.execute(
        select(func.count(APICallLog.id)).where(
            APICallLog.repo_id == repo.id
        )
    )
    total_calls = total_result.scalar() or 0
    
    # 总费用（从cost字段汇总）
    cost_result = await db.execute(
        select(func.sum(func.cast(APICallLog.cost, Numeric))).where(
            APICallLog.repo_id == repo.id
        )
    )
    total_cost = float(cost_result.scalar() or 0)
    
    # 活跃API Key数量
    from src.models.api_key import APIKey
    keys_result = await db.execute(
        select(func.count(APIKey.id)).where(
            and_(
                APIKey.user_id == repo.owner_id,
                APIKey.status == "active"
            )
        )
    )
    active_keys = keys_result.scalar() or 0
    
    return BaseResponse(
        data={
            "repo_id": str(repo.id),
            "total_calls": total_calls,
            "today_calls": today_calls,
            "week_calls": week_calls,
            "total_cost": round(total_cost, 2),
            "active_keys": active_keys,
            "avg_latency": 0,
            "success_rate": 100.0,
        }
    )


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
    If the repository has a configured backend URL, it will forward the request.
    Otherwise, it returns a mock response for testing purposes.
    
    Args:
        repo_slug: Repository slug
        request_data: Chat request data
    
    Returns:
        Chat response
    """
    import time
    import httpx
    from src.services.auth_service import AuthService
    
    start_time = time.time()
    
    # 1. 验证API Key并检查配额
    auth_service = AuthService(db)
    try:
        user, api_key = await auth_service.verify_api_key(x_access_key, repo_id=None)
    except Exception as e:
        from src.core.exceptions import QuotaExceededError, InvalidAPIKeyError
        if isinstance(e, (InvalidAPIKeyError, QuotaExceededError)):
            raise
        # 其他异常继续处理
    
    # 2. 获取仓库信息
    from src.models.repository import Repository
    repo_result = await db.execute(select(Repository).where(Repository.slug == repo_slug))
    repo = repo_result.scalar_one_or_none()
    
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # 3. 检查仓库状态
    if repo.status != "online":
        raise HTTPException(status_code=403, detail="Repository is not online")
    
    # 4. 尝试调用实际后端服务
    response_data = None
    status_code = 200
    
    if repo.endpoint_url:
        # 有配置后端URL，尝试调用
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                backend_url = f"{repo.endpoint_url.rstrip('/')}/chat"
                resp = await client.post(
                    backend_url,
                    json=request_data,
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": x_access_key,
                        "X-Request-ID": getattr(request.state, "request_id", ""),
                    }
                )
                status_code = resp.status_code
                if resp.status_code == 200:
                    response_data = resp.json()
                else:
                    response_data = {"error": resp.text}
        except httpx.TimeoutException:
            response_data = {"error": "Backend service timeout"}
            status_code = 504
        except httpx.RequestError as e:
            response_data = {"error": f"Backend service error: {str(e)}"}
            status_code = 502
    else:
        # 没有配置后端URL，返回模拟数据
        response_data = {
            "answer": "这是一个模拟的回答。在生产环境中，这将调用实际的心理问答API服务。",
            "suggestions": [
                "建议您保持规律的作息时间",
                "可以尝试冥想放松",
                "建议咨询专业心理医生",
            ],
        }
    
    # 5. 记录API调用日志并计费
    from src.models.billing import APICallLog
    from src.models.billing import Quota
    from datetime import datetime, timedelta
    from decimal import Decimal
    import json
    
    try:
        response_time = int((time.time() - start_time) * 1000)
        
        # 计算并扣除费用
        tokens_used = request_data.get("tokens_used", 0) if isinstance(request_data, dict) else 0
        call_cost, cost_description = await calculate_and_charge(
            db=db,
            user_id=user.id,
            repo_id=repo.id,
            api_key_id=api_key.id,
            tokens_used=tokens_used,
        )
        
        # 使用北京时间记录，保存 request_id 用于追踪
        log_entry = APICallLog(
            repo_id=repo.id,
            api_key_id=api_key.id,
            user_id=user.id,
            request_id=getattr(request.state, "request_id", None),
            endpoint="/chat",
            method="POST",
            request_params=json.dumps(request_data) if request_data else None,
            tester=getattr(user, "username", None) or getattr(user, "name", None) or getattr(user, "email", None),
            status_code=status_code,
            response_time=str(response_time),
            cost=str(call_cost),
            created_at=datetime.now(),  # 使用北京时间
        )
        db.add(log_entry)
        
        # 更新每日配额使用量
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        quota_result = await db.execute(
            select(Quota).where(
                and_(
                    Quota.key_id == api_key.id,
                    Quota.quota_type == "daily",
                    Quota.reset_at >= today_start
                )
            )
        )
        quota = quota_result.scalar_one_or_none()
        
        if quota:
            quota.quota_used += 1
        else:
            quota = Quota(
                user_id=user.id,
                key_id=api_key.id,
                repo_id=repo.id,
                quota_type="daily",
                quota_limit=api_key.daily_quota or 0,
                quota_used=1,
                reset_type="daily",
                reset_at=today_start + timedelta(days=1),
            )
            db.add(quota)
        
        await db.commit()
    except Exception as e:
        await db.rollback()
        print(f"Failed to log API call: {e}")
    
    return BaseResponse(
        data={
            **response_data,
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


@router.api_route("/{repo_slug}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_repository_endpoint(
    repo_slug: str,
    path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    通用仓库端点代理
    
    动态代理请求到仓库的实际后端服务。
    支持 GET、POST、PUT、DELETE、PATCH 方法。
    
    Args:
        repo_slug: 仓库 slug
        path: 仓库内部路径（如 weather/current）
    
    Returns:
        后端服务响应
    """
    import httpx
    from src.services.auth_service import AuthService
    
    # 1. 获取仓库信息
    repo_result = await db.execute(select(Repository).where(Repository.slug == repo_slug))
    repo = repo_result.scalar_one_or_none()
    
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_slug}' not found")
    
    # 2. 检查仓库状态
    if repo.status != "online":
        raise HTTPException(status_code=403, detail="Repository is not online")
    
    # 3. 如果没有配置后端URL，返回模拟响应
    if not repo.endpoint_url:
        return BaseResponse(
            code=200,
            message="Success",
            data={
                "mock": True,
                "repo": repo.name,
                "path": f"/{path}",
                "message": "后端服务未配置，返回模拟响应",
            }
        )
    
    # 4. 从请求头获取 API Key
    x_access_key = request.headers.get("X-Access-Key")
    
    # 5. 验证 API Key（必填）
    if not x_access_key:
        raise HTTPException(
            status_code=401,
            detail="API Key is required. Please provide X-Access-Key header."
        )
    
    auth_service = AuthService(db)
    try:
        user, key_obj = await auth_service.verify_api_key(x_access_key, repo_id=str(repo.id))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid API Key: {type(e).__name__}: {str(e)}")
    
    # 5. 转发请求到后端
    status_code = 200
    response_data = None
    response_time = 0
    
    try:
        # 构建后端 URL
        backend_url = f"{repo.endpoint_url.rstrip('/')}/{path}"
        
        # 获取查询参数
        query_params = dict(request.query_params)
        
        # 获取请求体
        body = await request.body()
        
        import time
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 构建转发请求
            headers = dict(request.headers)
            headers.pop("host", None)  # 移除 host 头
            
            if x_access_key:
                headers["X-API-Key"] = x_access_key
            
            resp = await client.request(
                method=request.method,
                url=backend_url,
                params=query_params,
                content=body if body else None,
                headers=headers,
            )
            
            status_code = resp.status_code
            response_time = int((time.time() - start_time) * 1000)
            
            # 返回后端响应
            try:
                resp_data = resp.json()
                response_data = resp_data
                return resp_data
            except Exception:
                response_data = {"status_code": resp.status_code, "content": resp.text}
                return {"status_code": resp.status_code, "content": resp.text}
                
    except httpx.TimeoutException:
        status_code = 504
        response_data = {"error": "Backend service timeout"}
        raise HTTPException(status_code=504, detail="Backend service timeout")
    except httpx.RequestError as e:
        status_code = 502
        response_data = {"error": f"Backend service error: {str(e)}"}
        raise HTTPException(status_code=502, detail=f"Backend service error: {str(e)}")
    finally:
        # 6. 记录 API 调用日志并计费
        try:
            from src.models.billing import APICallLog, Quota
            from datetime import datetime, timedelta
            import json
            
            # 合并请求参数（查询参数 + 请求体）
            request_params = dict(query_params)
            if body:
                try:
                    body_params = json.loads(body.decode('utf-8'))
                    if isinstance(body_params, dict):
                        request_params.update(body_params)
                except Exception:
                    pass
            
            # 计算并扣除费用
            tokens_used = response_data.get("tokens_used", 0) if isinstance(response_data, dict) else 0
            call_cost, cost_description = await calculate_and_charge(
                db=db,
                user_id=user.id,
                repo_id=repo.id,
                api_key_id=key_obj.id,
                tokens_used=tokens_used,
            )
            
            # 使用北京时间记录，保存 request_id 用于追踪
            log_entry = APICallLog(
                repo_id=repo.id,
                api_key_id=key_obj.id,
                user_id=user.id,
                request_id=getattr(request.state, "request_id", None),
                endpoint=f"/{path}",
                method=request.method,
                request_params=json.dumps(request_params) if request_params else None,
                tester=getattr(user, "username", None) or getattr(user, "name", None) or getattr(user, "email", None),
                status_code=status_code,
                response_time=str(response_time),
                cost=str(call_cost),
                created_at=datetime.now(),  # 使用北京时间
            )
            db.add(log_entry)
            
            # 更新每日配额使用量
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            quota_result = await db.execute(
                select(Quota).where(
                    and_(
                        Quota.key_id == key_obj.id,
                        Quota.quota_type == "daily",
                        Quota.reset_at >= today_start
                    )
                )
            )
            quota = quota_result.scalar_one_or_none()
            
            if quota:
                quota.quota_used += 1
            else:
                quota = Quota(
                    user_id=user.id,
                    key_id=key_obj.id,
                    repo_id=repo.id,
                    quota_type="daily",
                    quota_limit=key_obj.daily_quota or 0,
                    quota_used=1,
                    reset_type="daily",
                    reset_at=today_start + timedelta(days=1),
                )
                db.add(quota)
            
            await db.commit()
        except Exception as log_error:
            await db.rollback()
            print(f"Failed to log API call: {log_error}")


# ==================== 仓库所有者 CRUD 接口 ====================

from src.schemas.request import RepositoryCreate, RepositoryUpdate, RepositoryApproval, RepositoryReject


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
    
    # 检查用户权限（必须是 owner 类型）
    if current_user.user_type not in ['owner', 'super_admin']:
        raise AuthorizationError("只有仓库所有者可以创建仓库")
    
    # 生成 slug
    slug = repo_data.name.lower().replace("_", "-").replace(" ", "-")
    # 确保 slug 唯一
    existing = await db.execute(
        select(Repository).where(Repository.slug == slug)
    )
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid4().hex[:8]}"
    
    # 创建仓库
    repo = Repository(
        name=repo_data.name,
        slug=slug,
        display_name=repo_data.display_name or repo_data.name,
        description=repo_data.description,
        repo_type=repo_data.repo_type,
        protocol=repo_data.protocol or "http",
        status="pending",  # 初始状态为待审核
        owner_id=current_user.id,
        owner_type="external",  # 外部用户创建
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
    
    # 检查权限（必须是仓库所有者或超级管理员）
    if repo.owner_id != current_user.id and current_user.user_type != 'super_admin':
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
        repo.endpoint_url = repo_data.endpoint_url
    if repo_data.status is not None:
        repo.status = repo_data.status
        if repo_data.status == "online" and not repo.online_at:
            from datetime import datetime
            repo.online_at = datetime.utcnow()
    
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
    
    # 检查权限
    if repo.owner_id != current_user.id and current_user.user_type != 'super_admin':
        raise AuthorizationError("无权删除此仓库")
    
    await db.delete(repo)
    await db.commit()
    
    return BaseResponse(data={"message": "仓库删除成功"})


# ==================== 管理员仓库审核接口 ====================

def check_admin_permission(user: "User") -> None:  # noqa: F821
    """检查用户是否有管理员权限"""
    from src.core.exceptions import AuthorizationError
    if user.user_type not in ['admin', 'super_admin']:
        raise AuthorizationError("只有管理员可以执行此操作")


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
    from datetime import datetime
    
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
    repo.approved_at = datetime.utcnow()
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
    from datetime import datetime
    
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
    from datetime import datetime
    
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
    repo.online_at = datetime.utcnow()
    
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
    from datetime import datetime
    
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
    repo.offline_at = datetime.utcnow()
    
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
            created_at=repo.created_at,
            updated_at=repo.updated_at.isoformat() if repo.updated_at else None,
        )
    )


# ==================== 仓库端点管理 API ====================

def _check_repo_owner_permission(repo: Repository, user: "User") -> None:  # noqa: F821
    """检查仓库所有者权限"""
    if repo.owner_id != user.id and user.user_type != 'super_admin':
        from src.core.exceptions import AuthorizationError
        raise AuthorizationError("无权修改此仓库")


async def _get_repo_by_id(db: AsyncSession, repo_id: str) -> Optional[Repository]:
    """根据ID或slug获取仓库"""
    try:
        repo_uuid = UUID(repo_id) if len(repo_id) == 36 else None
    except ValueError:
        repo_uuid = None

    if repo_uuid:
        result = await db.execute(select(Repository).where(Repository.id == repo_uuid))
    else:
        result = await db.execute(select(Repository).where(Repository.slug == repo_id))
    return result.scalar_one_or_none()


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
    from datetime import datetime

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
        repo.endpoint_url = config_data.endpoint_url
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

    repo.updated_at = datetime.utcnow()
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
            created_at=repo.created_at,
            updated_at=repo.updated_at.isoformat() if repo.updated_at else None,
        )
    )
