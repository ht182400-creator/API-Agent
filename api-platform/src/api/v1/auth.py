"""Authentication API - 认证接口"""

from typing import Optional

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.schemas.response import BaseResponse, TokenResponse, SignatureResponse
from src.schemas.request import UserLogin, UserCreate
from src.core.security import (
    create_access_token,
    create_refresh_token,
    generate_signature,
    hash_password,
    verify_password,
)
from src.core.exceptions import AuthenticationError
from src.services.auth_service import get_current_user

router = APIRouter()


@router.post("/signature", response_model=BaseResponse[SignatureResponse])
async def generate_auth_signature(
    access_key: str,
    secret: str,
    method: str,
    path: str,
    body: Optional[str] = "",
):
    """
    Generate HMAC signature for API requests
    
    Args:
        access_key: API access key
        secret: API secret key
        method: HTTP method (GET, POST, etc.)
        path: Request path
        body: Request body (optional)
    
    Returns:
        Signature and authentication headers
    """
    signature, timestamp, nonce = generate_signature(
        access_key=access_key,
        secret=secret,
        method=method,
        path=path,
        body=body or "",
    )
    
    return BaseResponse(
        data=SignatureResponse(
            signature=signature,
            timestamp=timestamp,
            nonce=nonce,
            expires_at=int(timestamp) + 300000,  # 5 minutes
        )
    )


@router.post("/refresh", response_model=BaseResponse[TokenResponse])
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token
    
    Args:
        refresh_token: Refresh token
    
    Returns:
        New access token and refresh token
    """
    from src.core.security import verify_token
    
    try:
        payload = verify_token(refresh_token)
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")
        
        user_id = payload.get("sub")
        new_access_token = create_access_token({"sub": user_id})
        new_refresh_token = create_refresh_token({"sub": user_id})
        
        return BaseResponse(
            data=TokenResponse(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                expires_in=1800,  # 30 minutes
            )
        )
    except Exception as e:
        raise AuthenticationError(str(e))


@router.post("/register", response_model=BaseResponse[dict])
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account
    
    Args:
        user_data: User registration data (username, email, password, role)
    
    Returns:
        Created user information
    """
    from src.models.user import User
    from sqlalchemy import select, or_
    
    # 检查用户名是否已存在（如果提供了 username）
    if user_data.username:
        result = await db.execute(
            select(User).where(User.username == user_data.username)
        )
        if result.scalar_one_or_none():
            raise AuthenticationError("用户名已被注册")
    
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise AuthenticationError("邮箱已被注册")
    
    # 【V4.0 重构】统一使用 user_type，role 保留兼容
    # Validate role
    valid_roles = ["user", "developer", "admin", "super_admin"]
    if user_data.role not in valid_roles:
        raise AuthenticationError(f"无效的角色，可选值: {', '.join(valid_roles)}")
    
    # 【V4.0 重构】使用统一的权限配置
    from src.services.permission_service import DEFAULT_PERMISSIONS
    default_permissions = DEFAULT_PERMISSIONS
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    
    # 【V4.0 重构】统一设置 user_type 和 role
    # user_type 作为主要角色标识，role 保持兼容
    user_type = user_data.user_type or user_data.role
    
    new_user = User(
        username=user_data.username,  # 可能为 None
        email=user_data.email,
        password_hash=hashed_password,
        user_type=user_type,  # 统一使用 user_type
        role=user_data.role,   # role 保留用于兼容
        permissions=default_permissions.get(user_type, default_permissions.get(user_data.role, ["user:read"])),
        email_verified=False,
    )
    
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    
    return BaseResponse(
        data={
            "id": str(new_user.id),
            "username": new_user.username,
            "email": new_user.email,
            "user_type": new_user.user_type,
            "role": new_user.role,
            "created_at": new_user.created_at.isoformat(),
        }
    )


@router.post("/login", response_model=BaseResponse[TokenResponse])
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    User login (支持用户名或邮箱)
    
    Args:
        login_data: Login credentials (username 或 email)
    
    Returns:
        JWT tokens
    """
    from src.models.user import User
    from sqlalchemy import select, or_
    
    # Find user by username or email
    login_value = login_data.username or login_data.email
    
    if "@" in login_value:
        # 邮箱登录
        result = await db.execute(
            select(User).where(User.email == login_value)
        )
    else:
        # 用户名登录 - 查询 username 字段
        result = await db.execute(
            select(User).where(User.username == login_value)
        )
    
    user = result.scalar_one_or_none()
    
    if not user or not user.password_hash:
        raise AuthenticationError("用户名/邮箱或密码错误")
    
    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        raise AuthenticationError("用户名/邮箱或密码错误")
    
    # Check user status
    if user.user_status != "active":
        raise AuthenticationError("账户已被禁用")
    
    # Generate tokens (包含用户角色信息)
    token_data = {
        "sub": str(user.id),
        "role": user.role,
        "user_type": user.user_type,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return BaseResponse(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=1800,
        )
    )


@router.get("/me", response_model=BaseResponse[dict])
async def get_current_user_info(
    current_user = Depends(get_current_user),
):
    """
    获取当前登录用户信息
    
    Returns:
        User information (包含 username, role, permissions)
    """
    return BaseResponse(
        data={
            "id": str(current_user.id),
            "username": current_user.username,
            "email": current_user.email,
            "user_type": current_user.user_type,
            "user_status": current_user.user_status,
            "role": current_user.role,
            "permissions": current_user.permissions or [],
            "phone": current_user.phone,
            "vip_level": current_user.vip_level,
            "email_verified": current_user.email_verified,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
        }
    )


@router.post("/logout", response_model=BaseResponse[dict])
async def logout(
    current_user = Depends(get_current_user),
):
    """
    用户登出
    
    Returns:
        Success message
    """
    return BaseResponse(
        data={"message": "登出成功"},
        message="登出成功"
    )
