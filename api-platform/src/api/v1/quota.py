"""Quota API - 配额接口"""

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, Numeric, Float
from typing import Optional
import secrets
import uuid

from src.config.database import get_db
from src.schemas.response import BaseResponse
from src.schemas.request import CreateAPIKeyRequest
from src.services.auth_service import get_current_user
from src.models.user import User
from src.models.api_key import APIKey
from src.models.billing import Quota, APICallLog, Bill
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
    from src.models.billing import APICallLog
    
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
    
    # 统一使用北京时间，与日志记录时间保持一致
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today.replace(day=1)
    one_minute_ago = now - timedelta(minutes=1)
    one_hour_ago = now - timedelta(hours=1)
    
    # 查询配额记录
    quota_query = select(Quota).where(
        Quota.key_id == key_id
    )
    quota_result = await db.execute(quota_query)
    quotas = quota_result.scalars().all()
    
    # 计算今日和本月使用量 - 直接从 APICallLog 表统计
    daily_limit = api_key.daily_quota
    monthly_limit = api_key.monthly_quota

    # 今日使用量（直接统计 APICallLog）
    daily_result = await db.execute(
        select(func.count(APICallLog.id)).where(
            APICallLog.api_key_id == api_key.id,
            APICallLog.created_at >= today
        )
    )
    daily_used = daily_result.scalar() or 0

    # 本月使用量（直接统计 APICallLog）
    monthly_result = await db.execute(
        select(func.count(APICallLog.id)).where(
            APICallLog.api_key_id == api_key.id,
            APICallLog.created_at >= month_start
        )
    )
    monthly_used = monthly_result.scalar() or 0
    
    # 统计 RPM (最近1分钟调用次数) - 从 APICallLog 表
    # 按 api_key_id 过滤，确保统计的是当前 Key 的调用
    rpm_result = await db.execute(
        select(func.count(APICallLog.id)).where(
            APICallLog.api_key_id == api_key.id,
            APICallLog.created_at >= one_minute_ago
        )
    )
    rpm_used = rpm_result.scalar() or 0

    # 统计 RPH (最近1小时调用次数) - 从 APICallLog 表
    # 按 api_key_id 过滤，确保统计的是当前 Key 的调用
    rph_result = await db.execute(
        select(func.count(APICallLog.id)).where(
            APICallLog.api_key_id == api_key.id,
            APICallLog.created_at >= one_hour_ago
        )
    )
    rph_used = rph_result.scalar() or 0
    
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
            "rpm_limit": api_key.rate_limit_rpm or 1000,
            "rpm_used": rpm_used,
            "rph_limit": api_key.rate_limit_rph or 10000,
            "rph_used": rph_used,
            "balance_enabled": api_key.is_balance_enabled or False,
            "balance": 0,  # 余额需要单独从 Account 表获取
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
    from datetime import datetime, timedelta
    from src.models.billing import APICallLog
    
    # 获取用户的所有 keys
    keys_result = await db.execute(
        select(APIKey).where(APIKey.user_id == current_user.id)
    )
    keys = keys_result.scalars().all()
    
    # 统一使用北京时间，与日志记录时间保持一致
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today.replace(day=1)
    one_minute_ago = now - timedelta(minutes=1)
    one_hour_ago = now - timedelta(hours=1)

    overview = []
    for key in keys:
        daily_limit = key.daily_quota
        monthly_limit = key.monthly_quota

        # 今日使用量（直接统计 APICallLog）
        daily_result = await db.execute(
            select(func.count(APICallLog.id)).where(
                APICallLog.api_key_id == key.id,
                APICallLog.created_at >= today
            )
        )
        daily_used = daily_result.scalar() or 0

        # 本月使用量（直接统计 APICallLog）
        monthly_result = await db.execute(
            select(func.count(APICallLog.id)).where(
                APICallLog.api_key_id == key.id,
                APICallLog.created_at >= month_start
            )
        )
        monthly_used = monthly_result.scalar() or 0
        
        # 统计 RPM (最近1分钟) - 按 api_key_id 过滤
        rpm_result = await db.execute(
            select(func.count(APICallLog.id)).where(
                APICallLog.api_key_id == key.id,
                APICallLog.created_at >= one_minute_ago
            )
        )
        rpm_used = rpm_result.scalar() or 0

        # 统计 RPH (最近1小时) - 按 api_key_id 过滤
        rph_result = await db.execute(
            select(func.count(APICallLog.id)).where(
                APICallLog.api_key_id == key.id,
                APICallLog.created_at >= one_hour_ago
            )
        )
        rph_used = rph_result.scalar() or 0

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
            "rpm_limit": key.rate_limit_rpm or 1000,
            "rpm_used": rpm_used,
            "rph_limit": key.rate_limit_rph or 10000,
            "rph_used": rph_used,
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
    from src.models.billing import APICallLog
    from src.models.repository import Repository
    from datetime import datetime
    
    # 构建查询 - 查询 APICallLog 表（实际记录 API 调用的表）
    # 优先使用 api_key_id 过滤，与配额 API 统计口径保持一致
    if key_id:
        query = select(APICallLog).where(APICallLog.api_key_id == key_id)
        count_query = select(func.count(APICallLog.id)).where(APICallLog.api_key_id == key_id)
    else:
        # 未指定 key_id 时，使用 user_id 过滤（查看该用户所有调用）
        query = select(APICallLog).where(APICallLog.user_id == current_user.id)
        count_query = select(func.count(APICallLog.id)).where(APICallLog.user_id == current_user.id)

    if repo_id:
        query = query.where(APICallLog.repo_id == repo_id)
        count_query = count_query.where(APICallLog.repo_id == repo_id)
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.where(APICallLog.created_at >= start_dt)
            count_query = count_query.where(APICallLog.created_at >= start_dt)
        except Exception:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.where(APICallLog.created_at <= end_dt)
            count_query = count_query.where(APICallLog.created_at <= end_dt)
        except Exception:
            pass
    
    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    offset = (page - 1) * page_size
    query = query.order_by(desc(APICallLog.created_at)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # 获取仓库名称映射
    repo_ids = list(set(str(log.repo_id) for log in logs if log.repo_id))
    repo_names = {}
    if repo_ids:
        repo_result = await db.execute(
            select(Repository).where(Repository.id.in_(repo_ids))
        )
        for repo in repo_result.scalars().all():
            repo_names[str(repo.id)] = repo.display_name or repo.name
    
    return BaseResponse(
        data={
            "items": [
                {
                    "id": str(log.id),
                    "request_id": log.request_id,  # 全链路追踪ID
                    "api_key_id": str(log.api_key_id) if log.api_key_id else None,
                    "repo_id": str(log.repo_id) if log.repo_id else None,
                    "repo_name": repo_names.get(str(log.repo_id), "未知仓库"),
                    "endpoint": log.endpoint,
                    "method": log.request_method or log.method,
                    "request_params": log.request_params,  # 请求参数 (JSON字符串)
                    "tester": log.tester,  # 测试人员
                    "response_status": log.status_code,
                    "response_time": int(float(log.response_time)) if log.response_time else 0,
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
    获取配额使用历史 - 从 APICallLog 表统计
    """
    from datetime import datetime, timedelta
    
    # 使用北京时间
    now = datetime.now()
    start_date = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 从 APICallLog 表按日期聚合查询
    result = await db.execute(
        select(
            func.date(APICallLog.created_at).label("date"),
            func.count(APICallLog.id).label("call_count"),
            func.sum(func.cast(APICallLog.cost, Float)).label("total_amount")
        ).where(
            APICallLog.api_key_id == key_id,
            APICallLog.user_id == current_user.id,
            APICallLog.created_at >= start_date,
        ).group_by(func.date(APICallLog.created_at)).order_by(func.date(APICallLog.created_at))
    )
    rows = result.all()
    
    # 构建日期到数据的映射
    daily_data = {}
    for row in rows:
        date_val = row.date
        if hasattr(date_val, 'strftime'):
            date_str = date_val.strftime("%Y-%m-%d")
        else:
            date_str = str(date_val)
        daily_data[date_str] = {
            "date": date_str,
            "call_count": row.call_count or 0,
            "total_amount": float(row.total_amount or 0)
        }
    
    # 填充缺失的日期
    data = []
    for i in range(days - 1, -1, -1):
        date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        if date in daily_data:
            data.append(daily_data[date])
        else:
            data.append({"date": date, "call_count": 0, "total_amount": 0})
    
    return BaseResponse(data=data)


@router.get("/consumption-trend", response_model=BaseResponse[list])
async def get_consumption_trend(
    days: int = Query(14, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取每日消费趋势 - 从 Bill 表统计消费金额
    """
    from datetime import datetime, timedelta
    from src.models.billing import Bill

    # 使用北京时间
    now = datetime.now()
    start_date = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

    # 查询消费账单并按日期聚合
    result = await db.execute(
        select(Bill).where(
            Bill.user_id == current_user.id,
            Bill.bill_type == "consume",  # 与 billing.py 保持一致
            Bill.created_at >= start_date,
        ).order_by(Bill.created_at)
    )
    bills = result.scalars().all()

    # 按日期聚合消费金额
    daily_data = {}
    for bill in bills:
        date_str = bill.created_at.strftime("%Y-%m-%d") if bill.created_at else "unknown"
        if date_str not in daily_data:
            daily_data[date_str] = {"date": date_str, "amount": 0}
        # amount 存储为负数，取绝对值
        daily_data[date_str]["amount"] += abs(float(bill.amount))

    # 填充缺失的日期（返回完整的 days 天数据）
    data = []
    for i in range(days - 1, -1, -1):
        date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        data.append(daily_data.get(date, {"date": date, "amount": 0}))

    return BaseResponse(data=data)


@router.get("/top-repos/{key_id}", response_model=BaseResponse[list])
async def get_top_repos(
    key_id: str,
    limit: int = Query(10),
    days: int = Query(14),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取使用量最高的仓库 - 从 APICallLog 表统计
    """
    from datetime import datetime, timedelta
    from src.models.repository import Repository

    # 验证 key_id 属于当前用户
    key_result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id)
    )
    api_key = key_result.scalar_one_or_none()
    if not api_key:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("API Key不存在或无权访问")

    # 统一使用北京时间，与日志记录时间保持一致
    start_date = datetime.now() - timedelta(days=days)

    # 按 repo_id 聚合查询 - 使用 APICallLog 表，关联 Repository 获取仓库名称
    result = await db.execute(
        select(
            APICallLog.repo_id,
            func.count(APICallLog.id).label("call_count"),
        ).where(
            APICallLog.api_key_id == api_key.id,
            APICallLog.created_at >= start_date,
        ).group_by(APICallLog.repo_id).order_by(desc("call_count")).limit(limit)
    )
    rows = result.all()

    # 获取仓库名称
    data = []
    for row in rows:
        repo_name = "未知仓库"
        if row.repo_id:
            repo_result = await db.execute(
                select(Repository).where(Repository.id == row.repo_id)
            )
            repo = repo_result.scalar_one_or_none()
            if repo:
                repo_name = repo.name
        data.append({
            "repo_id": str(row.repo_id) if row.repo_id else None,
            "repo_name": repo_name,
            "total_amount": row.call_count,
            "call_count": row.call_count
        })

    return BaseResponse(data=data)
