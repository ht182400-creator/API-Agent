"""Authentication service - 认证服务"""

from typing import Optional, Tuple
from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.api_key import APIKey
from src.models.user import User
from src.core.security import verify_api_key, verify_hmac_signature, hash_api_key, verify_token
from src.core.exceptions import (
    InvalidAPIKeyError,
    APIKeyDisabledError,
    APIKeyExpiredError,
    AuthenticationError,
    TokenExpiredError,
)
from src.config.logging_config import get_logger
from src.config.database import get_db

# 模块日志记录器
logger = get_logger("auth")

# HTTP Bearer认证
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    获取当前登录用户
    
    从JWT token中获取用户信息
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
        )
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise TokenExpiredError("Token无效，请重新登录")
    
    user_id = payload.get("sub")
    if not user_id:
        raise TokenExpiredError("Token无效，请重新登录")
    
    # 从数据库获取用户
    result = await db.execute(select(User).where(User.id == user_id))
    # 安全处理：使用 scalars().all() 检查多记录情况
    users = result.scalars().all()
    if len(users) > 1:
        logger.warning(f"[Auth] Multiple users found for {user_id}, using first one")
        user = users[0]
    elif len(users) == 0:
        user = None
    else:
        user = users[0]
    
    if not user:
        raise TokenExpiredError("用户不存在，请重新登录")
    
    if user.user_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号已被禁用",
        )
    
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    【V4.0 重构】获取当前管理员用户
    
    验证当前用户是否为管理员
    """
    from src.services.permission_service import PermissionService
    
    if not PermissionService.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    
    # 返回用户信息字典
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "user_type": current_user.user_type,
        "role": current_user.role,
    }


async def get_current_super_admin_user(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    【V4.0 重构】获取当前超级管理员用户
    
    验证当前用户是否为超级管理员
    """
    from src.services.permission_service import PermissionService
    
    if not PermissionService.is_super_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限",
        )
    
    # 返回用户信息字典
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "user_type": current_user.user_type,
        "role": current_user.role,
    }


class AuthService:
    """Authentication service for API key and HMAC verification"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def verify_api_key(self, api_key: str, repo_id: str = None) -> Tuple[User, APIKey]:
        """
        Verify API key and return associated user and key
        
        Args:
            api_key: API key to verify
            repo_id: Repository ID (optional, for quota check)
        
        Returns:
            Tuple of (User, APIKey)
        
        Raises:
            InvalidAPIKeyError: If key is invalid
            APIKeyDisabledError: If key is disabled
            APIKeyExpiredError: If key has expired
            QuotaExceededError: If quota is exceeded
        """
        # Hash the provided key
        key_hash = hash_api_key(api_key)
        logger.debug("Verifying API key: %s...", api_key[:10] + "***")

        # Query key from database
        result = await self.db.execute(
            select(APIKey).where(APIKey.key_hash == key_hash)
        )
        key = result.scalar_one_or_none()

        if not key:
            logger.warning("API key not found: %s***", api_key[:10])
            raise InvalidAPIKeyError()

        # Check if key is active
        if key.status != "active":
            logger.warning("API key disabled: %s, status: %s", key.key_prefix, key.status)
            raise APIKeyDisabledError()

        # Check expiration
        if key.expires_at and key.expires_at < datetime.utcnow():
            logger.warning("API key expired: %s, expired at: %s", key.key_prefix, key.expires_at)
            raise APIKeyExpiredError()

        # Get associated user
        user_result = await self.db.execute(
            select(User).where(User.id == key.user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            logger.error("User not found for API key: %s", key.key_prefix)
            raise InvalidAPIKeyError()

        # Check user status
        if user.user_status != "active":
            logger.warning("User account disabled: %s, status: %s", user.email, user.user_status)
            raise APIKeyDisabledError()

        # Check rate limit / quota
        await self._check_rate_limit(key, repo_id)

        logger.info("API key verified successfully: %s for user: %s", key.key_prefix, user.email)
        return user, key

    async def _check_rate_limit(self, key: APIKey, repo_id: str = None) -> None:
        """
        检查API Key的限流/配额
        
        Args:
            key: API Key对象
            repo_id: 仓库ID
            
        Raises:
            QuotaExceededError: 如果超过配额
        """
        from src.models.billing import APICallLog, Quota
        from src.core.exceptions import QuotaExceededError
        from sqlalchemy import func, and_
        from datetime import datetime, timedelta
        import uuid
        
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 1. 检查每分钟请求数（RPM）- 使用Redis或数据库
        # 这里简化实现，实际应该使用Redis
        rpm_result = await self.db.execute(
            select(func.count(APICallLog.id)).where(
                and_(
                    APICallLog.api_key_id == key.id,
                    APICallLog.created_at >= now - timedelta(minutes=1)
                )
            )
        )
        rpm_count = rpm_result.scalar() or 0
        
        if key.rate_limit_rpm and rpm_count >= key.rate_limit_rpm:
            logger.warning("RPM limit exceeded: %s, rpm: %s/%s", key.key_prefix, rpm_count, key.rate_limit_rpm)
            raise QuotaExceededError(f"请求过于频繁，请稍后再试（RPM限制: {key.rate_limit_rpm}）")
        
        # 2. 检查小时请求数（RPH）
        rph_result = await self.db.execute(
            select(func.count(APICallLog.id)).where(
                and_(
                    APICallLog.api_key_id == key.id,
                    APICallLog.created_at >= now - timedelta(hours=1)
                )
            )
        )
        rph_count = rph_result.scalar() or 0
        
        if key.rate_limit_rph and rph_count >= key.rate_limit_rph:
            logger.warning("RPH limit exceeded: %s, rph: %s/%s", key.key_prefix, rph_count, key.rate_limit_rph)
            raise QuotaExceededError(f"小时请求数超限（RPH限制: {key.rate_limit_rph}）")
        
        # 3. 检查日配额（从Quota表）
        if key.daily_quota:
            # 查询今日使用量
            daily_used_result = await self.db.execute(
                select(func.coalesce(func.sum(Quota.quota_used), 0)).where(
                    and_(
                        Quota.key_id == key.id,
                        Quota.quota_type == "daily",
                        Quota.reset_at >= today_start
                    )
                )
            )
            daily_used = daily_used_result.scalar() or 0
            
            if daily_used >= key.daily_quota:
                logger.warning("Daily quota exceeded: %s, used: %s/%s", key.key_prefix, daily_used, key.daily_quota)
                raise QuotaExceededError(f"今日配额已用完，请明天再试（日配额: {key.daily_quota}）")
        
        # 4. 检查月配额
        if key.monthly_quota:
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_used_result = await self.db.execute(
                select(func.coalesce(func.sum(Quota.quota_used), 0)).where(
                    and_(
                        Quota.key_id == key.id,
                        Quota.quota_type == "monthly",
                        Quota.reset_at >= month_start
                    )
                )
            )
            monthly_used = monthly_used_result.scalar() or 0
            
            if monthly_used >= key.monthly_quota:
                logger.warning("Monthly quota exceeded: %s, used: %s/%s", key.key_prefix, monthly_used, key.monthly_quota)
                raise QuotaExceededError(f"本月配额已用完，请下个月再试（月配额: {key.monthly_quota}）")
        
        # 5. 检查账户余额（如果启用了余额扣费）
        if key.is_balance_enabled:
            from src.services.account_service import AccountService
            account_service = AccountService(self.db)
            balance = await account_service.get_balance(str(key.user_id))
            
            # 如果余额低于阈值，给出警告但不阻止（允许透支一定额度）
            min_balance = 1.0  # 最低余额1元
            if balance < min_balance:
                logger.warning("Low balance for API key: %s, balance: %s", key.key_prefix, balance)
                # 可以选择阻止或只是警告，这里选择警告而不是阻止

    async def verify_hmac_request(
        self,
        api_key: str,
        signature: str,
        timestamp: str,
        nonce: str,
        method: str,
        path: str,
        body: str = "",
    ) -> Tuple[User, APIKey]:
        """
        Verify HMAC signed request
        
        Args:
            api_key: API key
            signature: HMAC signature
            timestamp: Request timestamp
            nonce: Request nonce
            method: HTTP method
            path: Request path
            body: Request body
        
        Returns:
            Tuple of (User, APIKey)
        """
        # First verify the API key
        user, key = await self.verify_api_key(api_key)
        
        # Verify HMAC signature
        verify_hmac_signature(
            signature=signature,
            timestamp=timestamp,
            nonce=nonce,
            secret=key.secret_hash or "",
            method=method,
            path=path,
            body_hash=body,
        )
        
        return user, key

    async def create_api_key(
        self,
        user_id: str,
        name: str,
        auth_type: str = "api_key",
        rate_limit_rpm: int = 1000,
        rate_limit_rph: int = 10000,
        daily_quota: Optional[int] = None,
        monthly_quota: Optional[int] = None,
        allowed_repos: Optional[list] = None,
        denied_repos: Optional[list] = None,
    ) -> Tuple[str, str]:
        """
        Create a new API key for user
        
        Args:
            user_id: User ID
            name: Key name
            auth_type: Authentication type (api_key, hmac, jwt)
            rate_limit_rpm: Rate limit per minute
            rate_limit_rph: Rate limit per hour
            daily_quota: Daily quota limit
            monthly_quota: Monthly quota limit
            allowed_repos: List of allowed repository IDs
            denied_repos: List of denied repository IDs
        
        Returns:
            Tuple of (api_key, secret) - only returned on creation
        """
        from src.core.security import generate_api_key, generate_api_secret
        
        # Generate API key and secret
        prefix = "sk_live"
        api_key, key_hash = generate_api_key(prefix)
        secret = generate_api_secret()
        secret_hash = hash_api_key(secret)  # In production, use proper secret hashing
        
        # Create key record
        key = APIKey(
            user_id=user_id,
            key_name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            secret_hash=secret_hash,
            auth_type=auth_type,
            rate_limit_rpm=rate_limit_rpm,
            rate_limit_rph=rate_limit_rph,
            daily_quota=daily_quota,
            monthly_quota=monthly_quota,
            allowed_repos=allowed_repos,
            denied_repos=denied_repos,
            status="active",
        )
        
        self.db.add(key)
        await self.db.flush()
        await self.db.refresh(key)
        
        return api_key, secret

    async def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        """
        Revoke an API key
        
        Args:
            key_id: Key ID to revoke
            user_id: User ID (for authorization)
        
        Returns:
            True if revoked successfully
        """
        result = await self.db.execute(
            select(APIKey).where(
                APIKey.id == key_id,
                APIKey.user_id == user_id
            )
        )
        key = result.scalar_one_or_none()
        
        if not key:
            raise InvalidAPIKeyError()
        
        key.status = "disabled"
        key.disabled_at = datetime.utcnow()
        
        await self.db.flush()
        return True

    async def get_user_keys(self, user_id: str) -> list[APIKey]:
        """
        Get all API keys for a user
        
        Args:
            user_id: User ID
        
        Returns:
            List of API keys
        """
        result = await self.db.execute(
            select(APIKey).where(APIKey.user_id == user_id)
        )
        return result.scalars().all()
