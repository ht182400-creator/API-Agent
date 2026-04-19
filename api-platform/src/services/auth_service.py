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
    user = result.scalar_one_or_none()
    
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
    获取当前管理员用户
    
    验证当前用户是否为管理员
    """
    if current_user.user_type != "admin":
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
    获取当前超级管理员用户
    
    验证当前用户是否为超级管理员
    """
    if current_user.user_type != "super_admin":
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

    async def verify_api_key(self, api_key: str) -> Tuple[User, APIKey]:
        """
        Verify API key and return associated user and key
        
        Args:
            api_key: API key to verify
        
        Returns:
            Tuple of (User, APIKey)
        
        Raises:
            InvalidAPIKeyError: If key is invalid
            APIKeyDisabledError: If key is disabled
            APIKeyExpiredError: If key has expired
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

        logger.info("API key verified successfully: %s for user: %s", key.key_prefix, user.email)
        return user, key

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
