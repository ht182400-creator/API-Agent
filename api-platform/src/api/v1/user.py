"""
User API - 用户相关接口

提供用户升级、试用等功能
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.config.settings import settings
from src.config.logging_config import get_logger
from src.models.user import User

# 模块日志记录器
logger = get_logger("user")
from src.models.billing import Account, Bill
from src.models.api_key import APIKey
from src.models.repository import Repository
from src.schemas.response import BaseResponse
from src.services.auth_service import get_current_user
from src.services.billing_service import generate_bill_no
from src.core.exceptions import APIError


class HasReposResponse(BaseModel):
    """用户是否有仓库响应"""
    has_repos: bool
    repo_count: int

router = APIRouter(prefix="/user", tags=["用户"])


# ==================== 响应模型 ====================

class TrialConfigResponse(BaseModel):
    """试用配置响应"""
    trial_amount: float
    trial_enabled: bool
    trial_one_time_only: bool


# ==================== API 接口 ====================

@router.get("/config", response_model=BaseResponse[TrialConfigResponse])
async def get_trial_config():
    """
    获取试用配置
    
    返回试用功能的配置信息
    """
    return BaseResponse(
        data={
            "trial_amount": settings.trial_amount,
            "trial_enabled": settings.trial_enabled,
            "trial_one_time_only": settings.trial_one_time_only,
        }
    )


# ==================== 辅助函数 ====================

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


async def _is_real_developer(db: AsyncSession, user: User) -> dict:
    """
    【V4.0 重构】综合评估用户是否为真正的开发者
    
    评估维度：
    1. 使用 PermissionService.get_user_role() 统一获取角色
    2. developer 角色本身就是开发者
    3. 有仓库的用户也是开发者（仓库所有者）
    4. 是否有有效的 API Keys
    5. 是否有成功的充值记录
    
    Returns:
        dict: 包含评估结果和详细信息的字典
    """
    from src.services.permission_service import PermissionService
    
    # 【V4.0 重构】使用统一的角色获取
    user_role = PermissionService.get_user_role(user)
    
    result = {
        "is_developer": False,
        "role": user_role,  # 统一后的角色
        "role_match": user_role == "developer",  # 原: user.role == "developer"
        "user_type_match": user.user_type == "developer",
        "has_api_keys": False,
        "has_repos": False,
        "has_successful_recharge": False,
        "has_developer_permissions": False,
        "source": "unknown",
        "details": {}
    }
    
    # 检查 API Keys（只统计激活状态的）
    api_keys_result = await db.execute(
        select(func.count(APIKey.id))
        .where(APIKey.user_id == user.id)
        .where(APIKey.status == "active")
    )
    api_keys_count = api_keys_result.scalar() or 0
    result["has_api_keys"] = api_keys_count > 0
    
    # 检查仓库
    repos_result = await db.execute(
        select(func.count(Repository.id))
        .where(Repository.owner_id == user.id)
    )
    repos_count = repos_result.scalar() or 0
    result["has_repos"] = repos_count > 0
    
    # 检查成功的充值记录（只统计 completed 状态的 recharge）
    recharge_result = await db.execute(
        select(func.count(Bill.id))
        .where(Bill.user_id == user.id)
        .where(Bill.bill_type == "recharge")
        .where(Bill.status == "completed")
    )
    recharge_count = recharge_result.scalar() or 0
    result["has_successful_recharge"] = recharge_count > 0
    
    # 检查权限
    developer_perms = _get_developer_permissions()
    user_perms = user.permissions or []
    result["has_developer_permissions"] = any(p in user_perms for p in developer_perms)
    
    # 【V4.0 重构】综合判断 - 使用统一的角色判断
    # 优先1: 角色本身就是 developer 或更高级别
    if user_role in ["developer", "admin", "super_admin"]:
        result["is_developer"] = True
        result["source"] = "role_is_developer"
    
    # 优先2: 有仓库的用户（仓库所有者）
    elif repos_count > 0:
        result["is_developer"] = True
        result["source"] = "has_repos"
    
    # 优先3: 有成功的充值记录
    elif result["has_successful_recharge"]:
        result["is_developer"] = True
        result["source"] = "has_recharge"
    
    # 优先4: 有 API Keys
    elif result["has_api_keys"]:
        result["is_developer"] = True
        result["source"] = "has_api_keys"
    
    result["details"] = {
        "api_keys_count": api_keys_count,
        "repos_count": repos_count,
        "recharge_count": recharge_count,
        "role": user.role,
        "user_type": user.user_type,
        "permissions": user_perms,
    }
    
    return result


async def _get_account_or_create(db: AsyncSession, user: User) -> Account:
    """
    获取或创建用户账户
    
    注意：与 account_service.get_or_create_account 保持一致，使用 account_type="balance"
    """
    from sqlalchemy import and_
    from sqlalchemy.exc import IntegrityError
    
    try:
        result = await db.execute(
            select(Account).where(
                and_(
                    Account.user_id == user.id,
                    Account.account_type == "balance"
                )
            )
        )
        accounts = result.scalars().all()
        
        # 处理多记录情况
        if len(accounts) > 1:
            logger.warning(f"[Account] Multiple accounts found for user {user.id}, using first one")
            account = accounts[0]
        elif len(accounts) == 0:
            account = None
        else:
            account = accounts[0]
        
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
            await db.flush()  # 先 flush，让数据库检测约束冲突
            await db.commit()  # 需要 commit 才能持久化
            await db.refresh(account)
            logger.info(f"[UserAccount] Created new account for user {user.id}: balance={account.balance}")
        
        return account
    except IntegrityError:
        # 并发情况下，其他请求已创建了账户，回滚并重新查询
        logger.warning(f"[Account] Concurrent account creation detected for user {user.id}, fetching existing")
        await db.rollback()
        result = await db.execute(
            select(Account).where(
                and_(
                    Account.user_id == user.id,
                    Account.account_type == "balance"
                )
            )
        )
        account = result.scalars().first()
        if not account:
            raise RuntimeError(f"无法获取用户账户: {user.id}")
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
    注意：is_developer 综合评估多个字段，不只依赖 role 字段
    """
    # 获取账户信息
    account = await _get_account_or_create(db, current_user)
    
    # 综合评估是否为开发者
    developer评估 = await _is_real_developer(db, current_user)
    is_developer = developer评估["is_developer"]
    
    logger.info(f"[User Status] User {current_user.email}: role={current_user.role}, "
          f"user_type={current_user.user_type}, is_developer={is_developer}, "
          f"评估来源={developer评估['source']}, 详情={developer评估['details']}")
    
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


@router.get("/has-repos", response_model=BaseResponse[HasReposResponse])
async def check_user_has_repos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    【V4.2新增】检查用户是否有仓库
    
    用于前端判断是否显示仓库所有者相关菜单
    """
    from sqlalchemy import select, func
    from src.models.repository import Repository
    
    # 查询用户拥有的仓库数量
    result = await db.execute(
        select(func.count()).select_from(Repository).where(
            Repository.owner_id == current_user.id
        )
    )
    repo_count = result.scalar() or 0
    
    return BaseResponse(
        data=HasReposResponse(
            has_repos=repo_count > 0,
            repo_count=repo_count,
        )
    )


@router.post("/upgrade", response_model=BaseResponse[UpgradeResponse])
async def upgrade_to_developer(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    升级为开发者
    
    将普通用户(role=user)升级为开发者(role=developer)
    升级后用户将获得创建API、仓库等权限
    """
    # 记录升级前的状态
    old_role = current_user.role
    old_user_type = current_user.user_type
    old_permissions = current_user.permissions.copy() if current_user.permissions else []
    
    # 检查是否已经是开发者
    if current_user.role == "developer":
        raise APIError("您已经是开发者了，无需重复升级")
    
    # 不允许管理员角色降级为开发者
    if current_user.role in ["admin", "super_admin"]:
        raise APIError("管理员角色无法降级为普通开发者")
    
    # 升级用户角色
    current_user.role = "developer"
    current_user.user_type = "developer"
    current_user.permissions = _get_developer_permissions()
    current_user.updated_at = datetime.utcnow()
    
    # 记录操作日志
    try:
        from src.models.user_operation_log import UserOperationLog, OperationCategory, OperationAction, get_action_name
        from src.core.security import decode_token
        
        # 获取 session_id
        session_id = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                from src.core.security import verify_token
                payload = verify_token(token)
                session_id = payload.get("session_id")
            except:
                pass
        
        # 获取客户端信息
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:500] if request.headers.get("user-agent") else None
        
        # 解析 user-agent 获取设备信息
        device_type = "unknown"
        browser = None
        os_name = None
        if user_agent:
            ua_lower = user_agent.lower()
            if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
                device_type = "mobile"
            elif "tablet" in ua_lower or "ipad" in ua_lower:
                device_type = "tablet"
            else:
                device_type = "desktop"
            # 简单识别浏览器
            if "chrome" in ua_lower:
                browser = "Chrome"
            elif "firefox" in ua_lower:
                browser = "Firefox"
            elif "safari" in ua_lower:
                browser = "Safari"
            elif "edge" in ua_lower:
                browser = "Edge"
        
        # 创建操作日志
        log = UserOperationLog(
            user_id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            session_id=session_id,
            action=OperationAction.UPGRADE_SUCCESS,
            action_name=get_action_name(OperationAction.UPGRADE_SUCCESS),
            category=OperationCategory.UPGRADE,
            page="/user",
            page_name="用户首页",
            ip_address=client_ip,
            user_agent=user_agent,
            device_type=device_type,
            browser=browser,
            os=os_name,
            success=True,
            old_values={
                "role": old_role,
                "user_type": old_user_type,
                "permissions": old_permissions,
            },
            new_values={
                "role": current_user.role,
                "user_type": current_user.user_type,
                "permissions": current_user.permissions,
            },
        )
        db.add(log)
        
        logger.info(f"[User Upgrade - LOGGED] User {current_user.email} upgraded: {old_role} -> developer, logged")
    except Exception as e:
        # 日志记录失败不影响主流程
        logger.error(f"[User Upgrade - LOG ERROR] Failed to log: {e}")
    
    logger.info(f"[User Upgrade] User {current_user.email} upgraded: {old_role} -> developer")
    
    return BaseResponse(
        data={
            "role": current_user.role,
            "user_type": current_user.user_type,
            "permissions": current_user.permissions,
            "message": "升级成功！您现在可以使用开发者功能了",
        }
    )


# 升级费用常量
UPGRADE_FEE = 1.00  # 付费1元升级


@router.post("/upgrade-with-payment", response_model=BaseResponse[UpgradeResponse])
async def upgrade_with_payment(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    付费1元升级为开发者 (V4.1)
    
    用户支付1元后自动升级为开发者
    - 余额扣除1元
    - 创建账单记录
    - 记录操作日志
    """
    from src.services.account_service import AccountService
    from src.models.billing import Account
    
    logger = get_logger("user")
    
    # 1. 检查是否已经是开发者
    if current_user.role == "developer" or current_user.user_type == "developer":
        raise APIError("您已经是开发者了，无需重复升级")
    
    if current_user.role in ["admin", "super_admin"]:
        raise APIError("管理员角色无需升级")
    
    # 2. 获取用户账户余额
    account_service = AccountService(db)
    account = await account_service.get_or_create_account(str(current_user.id))
    balance = float(account.balance) if account and account.balance else 0
    
    # 3. 检查余额是否足够
    if balance < UPGRADE_FEE:
        raise APIError(
            f"余额不足，升级需要 ¥{UPGRADE_FEE:.2f}，"
            f"当前余额 ¥{balance:.2f}。请先充值后再升级。",
            code="INSUFFICIENT_BALANCE"
        )
    
    # 4. 记录升级前的状态
    old_role = current_user.role
    old_user_type = current_user.user_type
    old_balance = balance
    
    # 5. 扣除升级费用（创建账单记录）
    try:
        await account_service.deduct_balance(
            user_id=str(current_user.id),
            amount=UPGRADE_FEE,
            source_type="upgrade",
            source_id=None,
            description=f"付费升级：{old_role} → developer",
        )
        logger.info(f"[Upgrade-Payment] Deducted ¥{UPGRADE_FEE} from user {current_user.email}")
        # 【重要】立即提交扣费，确保余额更新被持久化
        await db.commit()
        # 刷新账户获取最新余额
        await db.refresh(account)
        logger.info(f"[Upgrade-Payment] Balance deduction committed: new_balance={account.balance}")
    except Exception as e:
        logger.error(f"[Upgrade-Payment] Failed to deduct balance: {e}")
        await db.rollback()
        raise APIError("扣费失败，请稍后重试")
    
    # 6. 升级用户角色
    current_user.role = "developer"
    current_user.user_type = "developer"
    current_user.permissions = _get_developer_permissions()
    current_user.updated_at = datetime.utcnow()
    
    # 7. 记录操作日志
    try:
        from src.models.user_operation_log import UserOperationLog, OperationCategory, OperationAction, get_action_name
        from src.core.security import decode_token
        
        # 获取 session_id
        session_id = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                from src.core.security import verify_token
                payload = verify_token(token)
                session_id = payload.get("session_id")
            except:
                pass
        
        # 获取客户端信息
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:500] if request.headers.get("user-agent") else None
        
        # 解析 user-agent
        device_type = "unknown"
        browser = None
        if user_agent:
            ua_lower = user_agent.lower()
            if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
                device_type = "mobile"
            elif "tablet" in ua_lower or "ipad" in ua_lower:
                device_type = "tablet"
            else:
                device_type = "desktop"
            if "chrome" in ua_lower:
                browser = "Chrome"
            elif "firefox" in ua_lower:
                browser = "Firefox"
            elif "safari" in ua_lower:
                browser = "Safari"
            elif "edge" in ua_lower:
                browser = "Edge"
        
        log = UserOperationLog(
            user_id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            session_id=session_id,
            action=OperationAction.UPGRADE_SUCCESS,
            action_name=get_action_name(OperationAction.UPGRADE_SUCCESS),
            category=OperationCategory.UPGRADE,
            page="/user",
            page_name="用户首页",
            ip_address=client_ip,
            user_agent=user_agent,
            device_type=device_type,
            browser=browser,
            success=True,
            old_values={
                "role": old_role,
                "user_type": old_user_type,
                "balance": old_balance,
            },
            new_values={
                "role": current_user.role,
                "user_type": current_user.user_type,
                "balance": old_balance - UPGRADE_FEE,
            },
            extra_data={
                "upgrade_fee": UPGRADE_FEE,
                "payment_type": "balance_deduction",
            }
        )
        db.add(log)
        logger.info(f"[Upgrade-Payment - LOGGED] User {current_user.email} upgraded with payment, logged")
    except Exception as e:
        logger.error(f"[Upgrade-Payment - LOG ERROR] Failed to log: {e}")
    
    logger.info(f"[Upgrade-Payment] User {current_user.email} upgraded: {old_role} -> developer, fee=¥{UPGRADE_FEE}")
    
    return BaseResponse(
        success=True,
        message=f"升级成功！已扣除 ¥{UPGRADE_FEE:.2f}，您现在是开发者了",
        data={
            "role": current_user.role,
            "user_type": current_user.user_type,
            "permissions": current_user.permissions,
        }
    )


@router.get("/upgrade-info", response_model=BaseResponse)
async def get_upgrade_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取升级信息 (V4.1)
    
    返回当前用户的升级信息和余额状态
    """
    from src.services.account_service import AccountService
    
    # 获取账户余额
    account_service = AccountService(db)
    account = await account_service.get_or_create_account(str(current_user.id))
    balance = float(account.balance) if account and account.balance else 0
    
    # 判断是否已是开发者
    is_developer = current_user.user_type == "developer" or current_user.role == "developer"
    
    return BaseResponse(
        data={
            "is_developer": is_developer,
            "upgrade_fee": UPGRADE_FEE,
            "current_balance": balance,
            "can_upgrade": balance >= UPGRADE_FEE and not is_developer,
            "balance_tip": f"当前余额 ¥{balance:.2f}，升级需 ¥{UPGRADE_FEE:.2f}" if not is_developer else "您已是开发者",
        }
    )


@router.post("/claim-trial", response_model=BaseResponse[ClaimTrialResponse])
async def claim_trial_amount(
    request: Request,
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
        raise APIError("试用功能已关闭，请联系管理员")
    
    # 检查是否已经领取过
    if settings.trial_one_time_only and current_user.trial_claimed:
        raise APIError(f"您已领取过试用金额({current_user.trial_amount_claimed}元)，无法重复领取")
    
    # 检查是否已经是开发者（开发者也可以领取，但不需要升级）
    if current_user.role == "developer":
        # 开发者直接领取试用金额
        account = await _get_account_or_create(db, current_user)
        old_balance = float(account.balance or 0)
        new_balance = old_balance + settings.trial_amount
        account.balance = str(new_balance)
        
        current_user.trial_claimed = True
        current_user.trial_amount_claimed = str(settings.trial_amount)
        current_user.updated_at = datetime.utcnow()
        
        # 记录账单
        bill = Bill(
            user_id=current_user.id,
            bill_no=generate_bill_no(),  # 生成账单号
            bill_type="bonus",
            amount=str(settings.trial_amount),
            balance_before=str(old_balance),
            balance_after=str(new_balance),
            description=f"试用金额",
            status="completed",
            environment="simulation" if settings.payment_mock_mode else "production",
        )
        db.add(bill)
        
        # 记录操作日志（开发者领取试用）
        try:
            from src.models.user_operation_log import UserOperationLog, OperationCategory, OperationAction, get_action_name
            log = UserOperationLog(
                user_id=current_user.id,
                username=current_user.username,
                email=current_user.email,
                action=OperationAction.TRIAL_SUCCESS,
                action_name=get_action_name(OperationAction.TRIAL_SUCCESS),
                category=OperationCategory.TRIAL,
                page="/user",
                page_name="用户首页",
                success=True,
                new_values={
                    "trial_amount": settings.trial_amount,
                    "new_balance": new_balance,
                    "old_balance": old_balance,
                    "role": current_user.role,
                },
                description=f"开发者领取试用金额: {settings.trial_amount}元",
            )
            db.add(log)
        except Exception as e:
            logger.error(f"[Trial Claim - LOG ERROR] {e}")
        
        # 【重要】提交事务，确保所有更改持久化
        await db.commit()
        
        return BaseResponse(
            data={
                "claimed": True,
                "amount": settings.trial_amount,
                "new_balance": new_balance,
                "message": f"领取成功！获得{settings.trial_amount}元试用金额",
            }
        )
    
    # 普通用户：领取试用金额 + 自动升级为开发者
    account = await _get_account_or_create(db, current_user)
    old_balance = float(account.balance or 0)
    new_balance = old_balance + settings.trial_amount
    account.balance = str(new_balance)
    
    # 记录升级前的状态
    old_role = current_user.role
    old_user_type = current_user.user_type
    old_permissions = current_user.permissions.copy() if current_user.permissions else []
    
    # 升级为开发者
    current_user.role = "developer"
    current_user.user_type = "developer"
    current_user.permissions = _get_developer_permissions()
    current_user.trial_claimed = True
    current_user.trial_amount_claimed = str(settings.trial_amount)
    current_user.updated_at = datetime.utcnow()
    
    # 记录账单
    bill = Bill(
        user_id=current_user.id,
        bill_no=generate_bill_no(),  # 生成账单号
        bill_type="bonus",
        amount=str(settings.trial_amount),
        balance_before=str(old_balance),
        balance_after=str(new_balance),
        description=f"试用金额（升级为开发者）",
        status="completed",
        environment="simulation" if settings.payment_mock_mode else "production",
    )
    db.add(bill)
    
    # 记录操作日志（普通用户领取试用 + 升级）
    try:
        from src.models.user_operation_log import UserOperationLog, OperationCategory, OperationAction, get_action_name
        log = UserOperationLog(
            user_id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            action=OperationAction.CLAIM_TRIAL,
            action_name=get_action_name(OperationAction.CLAIM_TRIAL),
            category=OperationCategory.TRIAL,
            page="/user",
            page_name="用户首页",
            success=True,
            old_values={
                "role": old_role,
                "user_type": old_user_type,
                "permissions": old_permissions,
                "balance": old_balance,
            },
            new_values={
                "role": current_user.role,
                "user_type": current_user.user_type,
                "permissions": current_user.permissions,
                "balance": new_balance,
                "trial_claimed": True,
                "trial_amount": settings.trial_amount,
            },
        )
        db.add(log)
        
        logger.info(f"[Trial Claim - LOGGED] User {current_user.email} claimed trial: {settings.trial_amount}元, upgraded: {old_role} -> developer")
    except Exception as e:
        logger.error(f"[Trial Claim - LOG ERROR] {e}")
    
    logger.info(f"[Trial Claim] User {current_user.email} claimed trial: {settings.trial_amount}元, upgraded: {old_role} -> developer")
    
    # 【重要】提交事务，确保所有更改持久化
    await db.commit()
    
    return BaseResponse(
        data={
            "claimed": True,
            "amount": settings.trial_amount,
            "new_balance": new_balance,
            "message": f"领取成功！获得{settings.trial_amount}元试用金额，已自动升级为开发者",
        }
    )
