"""Quota API - 配额接口"""

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, Numeric
from typing import Optional
import secrets
import uuid

from src.config.database import get_db
from src.schemas.response import BaseResponse
from src.schemas.request import CreateAPIKeyRequest
from src.services.auth_service import get_current_user
from src.models.user import User
from src.models.api_key import APIKey
from src.models.billing import Quota
from src.utils.crypto import hash_api_key, encrypt_api_key, decrypt_api_key

router = APIRouter()


# ============ API Keys 管理 ============

@router.get("/keys", response_model=BaseResponse[dict])
async def get_keys(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户的API Keys列表
    """
    # 获取总数
    count_query = select(func.count(APIKey.id)).where(APIKey.user_id == current_user.id)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    offset = (page - 1) * page_size
    query = (
        select(APIKey)
        .where(APIKey.user_id == current_user.id)
        .order_by(desc(APIKey.created_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    keys = result.scalars().all()
    
    return BaseResponse(
        data={
            "items": [
                {
                    "id": str(key.id),
                    "key_name": key.key_name,
                    "key_prefix": key.key_prefix,
                    "api_key": None,  # 不返回完整key
                    "status": key.status,
                    "auth_type": key.auth_type,
                    "rate_limit_rpm": key.rate_limit_rpm,
                    "rate_limit_rph": key.rate_limit_rph,
                    "daily_quota": key.daily_quota,
                    "monthly_quota": key.monthly_quota,
                    "last_used_at": key.last_call_at.isoformat() if key.last_call_at else None,
                    "created_at": key.created_at.isoformat() if key.created_at else None,
                    "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                }
                for key in keys
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            }
        }
    )


@router.post("/keys", response_model=BaseResponse[dict])
async def create_key(
    data: CreateAPIKeyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建新的API Key
    """
    # 生成 key
    key_prefix = f"sk_{secrets.token_hex(4)}"
    full_key = f"{key_prefix}_{secrets.token_hex(24)}"
    key_hash = hash_api_key(full_key)
    secret = secrets.token_hex(32)
    secret_hash = hash_api_key(secret)
    
    new_key = APIKey(
        user_id=current_user.id,
        key_name=data.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        secret_hash=secret_hash,
        encrypted_key=encrypt_api_key(full_key),  # 加密存储完整 key
        auth_type=data.auth_type or "api_key",
        allowed_repos=data.allowed_repos,
        denied_repos=data.denied_repos,
        rate_limit_rpm=data.rate_limit_rpm or 1000,
        rate_limit_rph=10000,  # 默认值
        daily_quota=data.daily_quota,
        monthly_quota=data.monthly_quota,
        status="active",
        expires_at=data.expires_at,
    )
    
    db.add(new_key)
    await db.flush()
    
    return BaseResponse(
        data={
            "id": str(new_key.id),
            "key_name": new_key.key_name,
            "key_prefix": new_key.key_prefix,
            "api_key": full_key,  # 创建时返回完整key
            "secret": secret,  # 创建时返回secret
            "status": new_key.status,
            "auth_type": new_key.auth_type,
            "rate_limit_rpm": new_key.rate_limit_rpm,
            "rate_limit_rph": new_key.rate_limit_rph,
            "daily_quota": new_key.daily_quota,
            "monthly_quota": new_key.monthly_quota,
            "created_at": new_key.created_at.isoformat() if new_key.created_at else None,
            "expires_at": new_key.expires_at.isoformat() if new_key.expires_at else None,
        }
    )


@router.get("/keys/{key_id}", response_model=BaseResponse[dict])
async def get_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取API Key详情
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        )
    )
    key = result.scalar_one_or_none()
    
    if not key:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("API Key不存在")
    
    return BaseResponse(
        data={
            "id": str(key.id),
            "key_name": key.key_name,
            "key_prefix": key.key_prefix,
            "api_key": None,
            "status": key.status,
            "auth_type": key.auth_type,
            "rate_limit_rpm": key.rate_limit_rpm,
            "rate_limit_rph": key.rate_limit_rph,
            "daily_quota": key.daily_quota,
            "monthly_quota": key.monthly_quota,
            "last_used_at": key.last_call_at.isoformat() if key.last_call_at else None,
            "created_at": key.created_at.isoformat() if key.created_at else None,
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
        }
    )


@router.put("/keys/{key_id}", response_model=BaseResponse[dict])
async def update_key(
    key_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新API Key
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        )
    )
    key = result.scalar_one_or_none()
    
    if not key:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("API Key不存在")
    
    # 更新字段
    if "key_name" in data:
        key.key_name = data["key_name"]
    if "rate_limit_rpm" in data:
        key.rate_limit_rpm = data["rate_limit_rpm"]
    if "rate_limit_rph" in data:
        key.rate_limit_rph = data["rate_limit_rph"]
    if "daily_quota" in data:
        key.daily_quota = data["daily_quota"]
    if "monthly_quota" in data:
        key.monthly_quota = data["monthly_quota"]
    
    await db.flush()
    
    return BaseResponse(data={"id": str(key.id), "message": "更新成功"})


@router.post("/keys/{key_id}/disable", response_model=BaseResponse[dict])
async def disable_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    禁用API Key
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        )
    )
    key = result.scalar_one_or_none()
    
    if not key:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("API Key不存在")
    
    key.status = "disabled"
    await db.flush()
    
    return BaseResponse(data={"id": key_id, "status": "disabled"})


@router.post("/keys/{key_id}/enable", response_model=BaseResponse[dict])
async def enable_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    启用API Key
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        )
    )
    key = result.scalar_one_or_none()
    
    if not key:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("API Key不存在")
    
    key.status = "active"
    await db.flush()
    
    return BaseResponse(data={"id": key_id, "status": "active"})


@router.delete("/keys/{key_id}", response_model=BaseResponse[dict])
async def delete_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    删除API Key
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        )
    )
    key = result.scalar_one_or_none()
    
    if not key:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("API Key不存在")
    
    await db.delete(key)
    await db.flush()
    
    return BaseResponse(data={"message": "删除成功"})


@router.post("/keys/{key_id}/set-quota", response_model=BaseResponse[dict])
async def set_quota(
    key_id: str,
    daily_quota: int = None,
    monthly_quota: int = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    设置配额限制
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        )
    )
    key = result.scalar_one_or_none()
    
    if not key:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("API Key不存在")
    
    if daily_quota is not None:
        key.daily_quota = daily_quota
    if monthly_quota is not None:
        key.monthly_quota = monthly_quota
    
    await db.flush()
    
    return BaseResponse(data={
        "id": key_id, 
        "daily_quota": key.daily_quota, 
        "monthly_quota": key.monthly_quota
    })


@router.get("/keys/{key_id}/reveal", response_model=BaseResponse[dict])
async def reveal_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    查看 API Key 明文（需要二次确认）
    警告：此操作会暴露敏感信息，仅在必要时调用
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        )
    )
    key = result.scalar_one_or_none()
    
    if not key:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("API Key不存在")
    
    if not key.encrypted_key:
        from src.core.exceptions import ServerError
        raise ServerError(
            "该 API Key 是旧数据创建，不支持查看完整内容。"
            "建议删除此 Key 并重新创建一个新的 Key，新创建的 Key 将支持查看功能。"
        )
    
    try:
        decrypted_key = decrypt_api_key(key.encrypted_key)
    except Exception as e:
        from src.core.exceptions import ServerError
        raise ServerError(
            "该 API Key 数据异常，无法解密查看。"
            "建议删除此 Key 并重新创建一个新的 Key。"
        )
    
    return BaseResponse(
        data={
            "id": str(key.id),
            "key_name": key.key_name,
            "api_key": decrypted_key,
            "key_prefix": key.key_prefix,
        }
    )


# ============ 配额信息 ============

@router.get("/info/{key_id}", response_model=BaseResponse[dict])
async def get_quota_info(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定Key的配额信息
    """
    from datetime import datetime, timedelta
    
    # 首先验证 API Key 属于当前用户
    key_result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        )
    )
    api_key = key_result.scalar_one_or_none()
    
    if not api_key:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("API Key不存在或无权访问")
    
    # 获取今日和本月使用量
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today.replace(day=1)
    
    # 查询配额记录
    quota_query = select(Quota).where(
        Quota.key_id == key_id
    )
    quota_result = await db.execute(quota_query)
    quotas = quota_result.scalars().all()
    
    # 计算今日和本月使用量
    daily_used = 0
    monthly_used = 0
    daily_limit = api_key.daily_quota
    monthly_limit = api_key.monthly_quota
    
    for q in quotas:
        if q.quota_type == "daily" and q.reset_at and q.reset_at >= today:
            daily_used = q.quota_used
        elif q.quota_type == "monthly" and q.reset_at and q.reset_at >= month_start:
            monthly_used = q.quota_used
    
    return BaseResponse(
        data={
            "api_key_id": key_id,
            "daily": {
                "used": daily_used,
                "limit": daily_limit or 0,
                "remaining": (daily_limit - daily_used) if daily_limit else None
            },
            "monthly": {
                "used": monthly_used,
                "limit": monthly_limit or 0,
                "remaining": (monthly_limit - monthly_used) if monthly_limit else None
            },
        }
    )


@router.get("/overview", response_model=BaseResponse[list])
async def get_quota_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取所有API Key的配额概览
    """
    # 获取用户的所有 keys
    keys_result = await db.execute(
        select(APIKey).where(APIKey.user_id == current_user.id)
    )
    keys = keys_result.scalars().all()
    
    overview = []
    for key in keys:
        # 获取每个 key 的配额
        quota_result = await db.execute(
            select(Quota).where(Quota.key_id == str(key.id))
        )
        quotas = quota_result.scalars().all()
        
        daily_used = 0
        monthly_used = 0
        daily_limit = key.daily_quota
        monthly_limit = key.monthly_quota
        
        for q in quotas:
            if q.quota_type == "daily":
                daily_used = q.quota_used
            elif q.quota_type == "monthly":
                monthly_used = q.quota_used
        
        overview.append({
            "api_key_id": str(key.id),
            "daily": {
                "used": daily_used,
                "limit": daily_limit or 0,
                "remaining": (daily_limit - daily_used) if daily_limit else None
            },
            "monthly": {
                "used": monthly_used,
                "limit": monthly_limit or 0,
                "remaining": (monthly_limit - monthly_used) if monthly_limit else None
            },
        })
    
    return BaseResponse(data=overview)


# ============ 调用日志 ============

@router.get("/logs", response_model=BaseResponse[dict])
async def get_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    key_id: str = Query(None),
    repo_id: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取调用日志
    """
    from src.models.api_key import KeyUsageLog
    from datetime import datetime
    
    # 构建查询
    query = select(KeyUsageLog).where(KeyUsageLog.user_id == current_user.id)
    
    if key_id:
        query = query.where(KeyUsageLog.key_id == key_id)
    if repo_id:
        query = query.where(KeyUsageLog.repo_id == repo_id)
    
    # 获取总数
    count_query = select(func.count(KeyUsageLog.id)).where(KeyUsageLog.user_id == current_user.id)
    if key_id:
        count_query = count_query.where(KeyUsageLog.key_id == key_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    offset = (page - 1) * page_size
    query = query.order_by(desc(KeyUsageLog.created_at)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return BaseResponse(
        data={
            "items": [
                {
                    "id": str(log.id),
                    "api_key_id": str(log.key_id),
                    "repo_id": str(log.repo_id) if log.repo_id else None,
                    "repo_name": None,  # 需要关联查询
                    "endpoint": log.endpoint,
                    "method": log.method,
                    "response_status": log.status_code,
                    "response_time": log.latency_ms,
                    "ip_address": log.ip_address,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            }
        }
    )


@router.get("/usage-history/{key_id}", response_model=BaseResponse[list])
async def get_usage_history(
    key_id: str,
    period_type: str = Query("daily"),
    days: int = Query(14),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取配额使用历史
    """
    from datetime import datetime, timedelta
    from src.models.api_key import KeyUsageLog
    
    start_date = datetime.now() - timedelta(days=days)
    
    # 按日期聚合查询
    result = await db.execute(
        select(KeyUsageLog).where(
            KeyUsageLog.key_id == key_id,
            KeyUsageLog.user_id == current_user.id,
            KeyUsageLog.created_at >= start_date,
        ).order_by(KeyUsageLog.created_at)
    )
    logs = result.scalars().all()
    
    # 按日期聚合
    daily_data = {}
    for log in logs:
        date_str = log.created_at.strftime("%Y-%m-%d") if log.created_at else "unknown"
        if date_str not in daily_data:
            daily_data[date_str] = {
                "date": date_str,
                "total_amount": float(log.cost or "0"),
                "call_count": 0
            }
        daily_data[date_str]["call_count"] += 1
        daily_data[date_str]["total_amount"] += float(log.cost or "0")
    
    return BaseResponse(
        data=list(daily_data.values()) if daily_data else []
    )


@router.get("/top-repos/{key_id}", response_model=BaseResponse[list])
async def get_top_repos(
    key_id: str,
    limit: int = Query(10),
    days: int = Query(14),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取使用量最高的仓库
    """
    from datetime import datetime, timedelta
    from src.models.api_key import KeyUsageLog
    
    start_date = datetime.now() - timedelta(days=days)
    
    # 按 repo_id 聚合查询
    result = await db.execute(
        select(
            KeyUsageLog.repo_id,
            func.count(KeyUsageLog.id).label("call_count"),
            func.sum(func.cast(KeyUsageLog.cost, Numeric)).label("total_amount")
        ).where(
            KeyUsageLog.key_id == key_id,
            KeyUsageLog.user_id == current_user.id,
            KeyUsageLog.created_at >= start_date,
        ).group_by(KeyUsageLog.repo_id).order_by(desc("call_count")).limit(limit)
    )
    rows = result.all()
    
    return BaseResponse(
        data=[
            {
                "repo_id": str(row.repo_id) if row.repo_id else None,
                "repo_name": "未知仓库",  # 需要关联查询
                "total_amount": float(row.total_amount or 0),
                "call_count": row.call_count
            }
            for row in rows
        ]
    )
