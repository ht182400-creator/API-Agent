"""
仓库接口 —— 共享辅助（`src/api/v1/repositories.py` 拆分产物）

由 `scripts/dev/split_api_router.py` 从 `src/api/v1/repositories.py` 精确搬移生成，
函数体与原实现逐字一致（仅移动位置）。
"""

from typing import Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, Numeric
from src.schemas.response import BaseResponse
from src.core.exceptions import AuthorizationError
from src.utils.url_safety import ensure_outbound_url_allowed, OutboundURLBlocked
from src.utils.time_range import cst_now, cst_day_range_utc
from src.models.repository import Repository, RepoPricing
from uuid import UUID




# ==================== 安全辅助函数 ====================

def _validate_endpoint_url(endpoint_url: Optional[str]) -> Optional[str]:
    """
    校验仓库后端地址（**写入侧** SSRF 防护，评审项 N-1）。

    与转发时的请求侧校验形成双重防护：在仓库创建/更新阶段即拒绝非法地址，
    避免脏数据落库后才在调用时暴露问题。

    Args:
        endpoint_url: 待校验地址（可为空，表示未配置后端）

    Returns:
        去除首尾空白后的地址；输入为空时返回 None

    Raises:
        HTTPException(400): 地址非法（协议不支持 / 内网地址 / 元数据地址 / 无法解析）
    """
    if not endpoint_url or not str(endpoint_url).strip():
        return None

    from src.config.settings import settings as _settings

    candidate = str(endpoint_url).strip()
    try:
        ensure_outbound_url_allowed(
            candidate,
            allow_private=_settings.private_repo_endpoints_allowed,
        )
    except OutboundURLBlocked as exc:
        raise HTTPException(status_code=400, detail=f"仓库后端地址不被允许: {exc}")

    return candidate


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
        # 没有账户，不扣费，但抛出余额不足异常阻止调用
        raise HTTPException(
            status_code=402,
            detail=f"账户不存在或余额为0，无法调用API。请先充值。"
        )
    
    # 检查余额是否足够
    balance = Decimal(str(account.balance))
    if balance < cost:
        # 余额不足，拒绝API调用
        raise HTTPException(
            status_code=402,
            detail=f"余额不足。当前余额：¥{balance:.2f}，本次调用需要：¥{cost:.2f}。请先充值。"
        )
    
    # 扣费
    balance_before = balance
    balance_after = balance - cost
    account.balance = str(balance_after)
    account.total_consume = str(Decimal(str(account.total_consume)) + cost)
    
    # 获取环境标识（唯一数据源：settings.billing_environment）
    environment = settings.billing_environment
    
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
