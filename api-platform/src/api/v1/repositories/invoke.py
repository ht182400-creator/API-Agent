"""
仓库接口 —— 仓库能力调用（对话 / 翻译 / 识别）

由 `scripts/dev/split_api_router.py` 从 `src/api/v1/repositories.py` 精确搬移生成，
函数体与原实现逐字一致（仅移动位置）。
"""

from fastapi import Depends, Request, Header, HTTPException, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from src.config.database import get_db
from src.schemas.response import BaseResponse
from src.utils.url_safety import ensure_outbound_url_allowed, OutboundURLBlocked
from src.utils.sanitize import sanitize
from src.models.repository import Repository
from src.api.v1.repositories._shared import calculate_and_charge

router = APIRouter()




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
            backend_url = f"{repo.endpoint_url.rstrip('/')}/chat"

            # 【安全】SSRF 防护：校验出站地址（协议/内网/元数据地址）
            from src.config.settings import settings as _settings
            ensure_outbound_url_allowed(
                backend_url,
                allow_private=_settings.private_repo_endpoints_allowed,
            )

            async with httpx.AsyncClient(timeout=30.0) as client:
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
        except OutboundURLBlocked as e:
            response_data = {"error": f"仓库后端地址不被允许: {e}"}
            status_code = 403
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
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal
    import json
    
    try:
        response_time = int((time.time() - start_time) * 1000)
        
        # 计算并扣除费用（余额不足会抛出 HTTPException 402）
        tokens_used = request_data.get("tokens_used", 0) if isinstance(request_data, dict) else 0
        call_cost, cost_description = await calculate_and_charge(
            db=db,
            user_id=user.id,
            repo_id=repo.id,
            api_key_id=api_key.id,
            tokens_used=tokens_used,
        )
        
        log_entry = APICallLog(
            repo_id=repo.id,
            api_key_id=api_key.id,
            user_id=user.id,
            request_id=getattr(request.state, "request_id", None),
            endpoint="/chat",
            method="POST",
            request_params=json.dumps(sanitize(request_data), ensure_ascii=False) if request_data else None,
            tester=getattr(user, "username", None) or getattr(user, "name", None) or getattr(user, "email", None),
            status_code=status_code,
            response_time=str(response_time),
            cost=str(call_cost),
            created_at=datetime.now(timezone.utc),
        )
        db.add(log_entry)
        
        # 更新每日配额使用量
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
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
    except HTTPException:
        # HTTPException（如余额不足）正常抛出
        await db.rollback()
        raise
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
