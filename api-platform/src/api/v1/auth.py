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
        user_data: User registration data
    
    Returns:
        Created user information
    """
    from src.models.user import User
    from sqlalchemy import select
    
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise AuthenticationError("Email already registered")
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        user_type=user_data.user_type,
        email_verified=False,
    )
    
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    
    return BaseResponse(
        data={
            "id": str(new_user.id),
            "email": new_user.email,
            "user_type": new_user.user_type,
            "created_at": new_user.created_at.isoformat(),
        }
    )


@router.post("/login", response_model=BaseResponse[TokenResponse])
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    User login
    
    Args:
        login_data: Login credentials
    
    Returns:
        JWT tokens
    """
    from src.models.user import User
    from sqlalchemy import select
    
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == login_data.email)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.password_hash:
        raise AuthenticationError("Invalid email or password")
    
    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        raise AuthenticationError("Invalid email or password")
    
    # Check user status
    if user.user_status != "active":
        raise AuthenticationError("Account is disabled")
    
    # Generate tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return BaseResponse(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=1800,
        )
    )
