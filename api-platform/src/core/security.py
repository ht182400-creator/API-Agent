"""Security module - 安全认证模块"""

import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.config.settings import settings
from src.core.exceptions import (
    InvalidAPIKeyError,
    InvalidSignatureError,
    TimestampExpiredError,
)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using configured algorithm.
    
    Algorithm selection based on settings.password_hash_mode:
    - "bcrypt": Use bcrypt (recommended, default)
    - "sha256": Use SHA256 (faster, less secure)
    - "auto": Use bcrypt
    """
    mode = settings.password_hash_mode
    
    if mode == "sha256":
        return hashlib.sha256(password.encode()).hexdigest()
    else:
        # bcrypt is recommended, auto also uses bcrypt
        return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Supports multiple hash formats:
    - bcrypt (starts with $2)
    - SHA256 (64 hex characters)
    
    Always tries bcrypt first, then falls back to SHA256.
    """
    if not hashed_password:
        return False
    
    # 如果是 bcrypt 格式 (以 $2 开头)
    if hashed_password.startswith('$2'):
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False
    
    # 如果是 SHA256 格式 (64个字符的十六进制)
    if len(hashed_password) == 64:
        try:
            hashed = hashlib.sha256(plain_password.encode()).hexdigest()
            return hmac.compare_digest(hashed, hashed_password)
        except Exception:
            return False
    
    # 尝试 passlib 自动识别
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key(prefix: str = "sk_live") -> tuple[str, str]:
    """Generate a new API key"""
    import secrets

    random_part = secrets.token_urlsafe(32)
    api_key = f"{prefix}_{random_part}"
    key_hash = hash_api_key(api_key)
    return api_key, key_hash


def generate_api_secret() -> str:
    """Generate API secret for HMAC authentication"""
    import secrets

    return secrets.token_urlsafe(32)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise InvalidAPIKeyError()


def verify_api_key(provided_key: str, stored_hash: str) -> bool:
    """Verify an API key against stored hash"""
    provided_hash = hash_api_key(provided_key)
    return hmac.compare_digest(provided_hash, stored_hash)


def verify_hmac_signature(
    signature: str,
    timestamp: str,
    nonce: str,
    secret: str,
    method: str,
    path: str,
    body_hash: str = "",
) -> bool:
    """Verify HMAC signature for API requests"""
    # Check timestamp (5 minutes tolerance)
    try:
        request_time = int(timestamp)
        current_time = int(time.time() * 1000)
        if abs(current_time - request_time) > 300000:  # 5 minutes
            raise TimestampExpiredError()
    except ValueError:
        raise InvalidSignatureError()

    # Build string to sign
    string_to_sign = "\n".join(
        [
            f"AccessKey={secret[:20]}",
            f"Timestamp={timestamp}",
            f"Nonce={nonce}",
            f"Method={method.upper()}",
            f"Path={path}",
            f"BodyHash={body_hash}",
        ]
    )

    # Calculate expected signature
    expected_signature = hmac.new(
        secret.encode(),
        string_to_sign.encode(),
        hashlib.sha256,
    ).hexdigest()

    # Compare signatures
    if not hmac.compare_digest(signature, expected_signature):
        raise InvalidSignatureError()

    return True


def generate_signature(
    access_key: str,
    secret: str,
    method: str,
    path: str,
    body: str = "",
) -> tuple[str, str, str]:
    """Generate HMAC signature for API requests"""
    timestamp = str(int(time.time() * 1000))
    nonce = hashlib.md5(f"{timestamp}{secret}".encode()).hexdigest()
    body_hash = hashlib.sha256(body.encode()).hexdigest() if body else ""

    string_to_sign = "\n".join(
        [
            f"AccessKey={access_key}",
            f"Timestamp={timestamp}",
            f"Nonce={nonce}",
            f"Method={method.upper()}",
            f"Path={path}",
            f"BodyHash={body_hash}",
        ]
    )

    signature = hmac.new(
        secret.encode(),
        string_to_sign.encode(),
        hashlib.sha256,
    ).hexdigest()

    return signature, timestamp, nonce
