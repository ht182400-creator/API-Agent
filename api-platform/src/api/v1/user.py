"""
User API - 用户相关接口

提供用户升级、试用等功能
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.config.settings import settings
from src.models.user import User
from src.models.billing import Account, Bill
from src.schemas.response import BaseResponse
from src.services.auth_service import get_current_user
from src.core.exceptions import BusinessError

router = APIRouter(prefix="/user", tags=["用户"])


# ==================== 响应模型 ====================

class UpgradeResponse(BaseModel):
    """升级响应"""
    role: str
    user_type: str
    permissions: list
    message: str


class ClaimTrialResponse(BaseModel):
    """领取试用响应"""
    claimed: bool
    amount: float
    new_balance: float
    message: str


class UserStatusResponse(BaseModel):
    """用户状态响应"""
    user_id: str
    role: str
    user_type: str
    permissions: list
    balance: float
    trial_claimed: bool
    trial_amount_claimed: float
    is_developer: bool


# ==================== 辅助函数 ====================

def _get_developer_permissions() -> list:
    """获取开发者默认权限"""
    return ["user:read", "user:write", "api:read", "api:write"]


def _get_account_or_create(db: AsyncSession, user: User) -> Account:
    """获取或创建用户账户"""
    result = db.execute(
        select(Account).where(Account.user_id == user.id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        account = Account(
            user_id=user.id,
            account_type="balance",
            balance="0",
            frozen_balance="0",
            total_recharge="0",
            total_consume="0",
        )
        db.add(account)
        db.flush()
    
    return account


# ==================== API 接口 ====================

@router.get("/status", response_model=BaseResponse[UserStatusResponse])
async def get_user_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户状态
    
    返回用户的角色、权限、余额等信息
    """
    # 获取账户信息
    account = _get_account_or_create(db, current_user)
    
    # 判断是否是开发者
    is_developer = current_user.role == "developer"
    
    return BaseResponse(
        data={
            "user_id": str(current_user.id),
            "role": current_user.role,
            "user_type": current_user.user_type,
            "permissions": current_user.permissions or [],
            "balance": float(account.balance or 0),
            "trial_claimed": current_user.trial_claimed or False,
            "trial_amount_claimed": float(current_user.trial_amount_claimed or 0),
            "is_developer": is_developer,
        }
    )


@router.post("/upgrade", response_model=BaseResponse[UpgradeResponse])
async def upgrade_to_developer(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    升级为开发者
    
    将普通用户(role=user)升级为开发者(role=developer)
    升级后用户将获得创建API、仓库等权限
    """
    # 检查是否已经是开发者
    if current_user.role == "developer":
        raise BusinessError("您已经是开发者了，无需重复升级")
    
    # 不允许管理员角色降级为开发者
    if current_user.role in ["admin", "super_admin"]:
        raise BusinessError("管理员角色无法降级为普通开发者")
    
    # 升级用户角色
    old_role = current_user.role
    current_user.role = "developer"
    current_user.user_type = "developer"
    current_user.permissions = _get_developer_permissions()
    current_user.updated_at = datetime.utcnow()
    
    print(f"[User Upgrade] User {current_user.email} upgraded: {old_role} -> developer")
    
    return BaseResponse(
        data={
            "role": current_user.role,
            "user_type": current_user.user_type,
            "permissions": current_user.permissions,
            "message": "升级成功！您现在可以使用开发者功能了",
        }
    )


@router.post("/claim-trial", response_model=BaseResponse[ClaimTrialResponse])
async def claim_trial_amount(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    领取试用金额
    
    新用户可以领取一次试用金额，用于体验平台功能
    - 试用金额: 10元（可配置）
    - 每个用户只能领取一次
    """
    # 检查试用功能是否启用
    if not settings.trial_enabled:
        raise BusinessError("试用功能已关闭，请联系管理员")
    
    # 检查是否已经领取过
    if settings.trial_one_time_only and current_user.trial_claimed:
        raise BusinessError(f"您已领取过试用金额({current_user.trial_amount_claimed}元)，无法重复领取")
    
    # 检查是否已经是开发者（开发者也可以领取，但不需要升级）
    if current_user.role == "developer":
        # 开发者直接领取试用金额
        account = _get_account_or_create(db, current_user)
        old_balance = float(account.balance or 0)
        new_balance = old_balance + settings.trial_amount
        account.balance = str(new_balance)
        
        current_user.trial_claimed = True
        current_user.trial_amount_claimed = str(settings.trial_amount)
        current_user.updated_at = datetime.utcnow()
        
        # 记录账单
        bill = Bill(
            user_id=current_user.id,
            bill_type="bonus",
            amount=str(settings.trial_amount),
            balance_before=str(old_balance),
            balance_after=str(new_balance),
            description=f"试用金额",
            status="completed",
            environment="simulation" if settings.payment_mock_mode else "production",
        )
        db.add(bill)
        
        return BaseResponse(
            data={
                "claimed": True,
                "amount": settings.trial_amount,
                "new_balance": new_balance,
                "message": f"领取成功！获得{settings.trial_amount}元试用金额",
            }
        )
    
    # 普通用户：领取试用金额 + 自动升级为开发者
    account = _get_account_or_create(db, current_user)
    old_balance = float(account.balance or 0)
    new_balance = old_balance + settings.trial_amount
    account.balance = str(new_balance)
    
    # 升级为开发者
    old_role = current_user.role
    current_user.role = "developer"
    current_user.user_type = "developer"
    current_user.permissions = _get_developer_permissions()
    current_user.trial_claimed = True
    current_user.trial_amount_claimed = str(settings.trial_amount)
    current_user.updated_at = datetime.utcnow()
    
    # 记录账单
    bill = Bill(
        user_id=current_user.id,
        bill_type="bonus",
        amount=str(settings.trial_amount),
        balance_before=str(old_balance),
        balance_after=str(new_balance),
        description=f"试用金额（升级为开发者）",
        status="completed",
        environment="simulation" if settings.payment_mock_mode else "production",
    )
    db.add(bill)
    
    print(f"[Trial Claim] User {current_user.email} claimed trial: {settings.trial_amount}元, upgraded: {old_role} -> developer")
    
    return BaseResponse(
        data={
            "claimed": True,
            "amount": settings.trial_amount,
            "new_balance": new_balance,
            "message": f"领取成功！获得{settings.trial_amount}元试用金额，已自动升级为开发者",
        }
    )
