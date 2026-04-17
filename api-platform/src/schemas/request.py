"""Request schemas - 请求模型"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """User creation request"""

    email: EmailStr
    password: str = Field(..., min_length=8)
    user_type: str = Field(default="developer")
    nickname: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    """User login request"""

    email: EmailStr
    password: str


class APIKeyCreate(BaseModel):
    """API Key creation request"""

    name: str = Field(..., min_length=1, max_length=100)
    user_id: Optional[str] = None  # For admin creating keys for users
    allowed_repos: Optional[List[str]] = None
    denied_repos: Optional[List[str]] = None
    rate_limit_rpm: int = Field(default=1000, ge=1, le=10000)
    daily_quota: Optional[int] = None
    monthly_quota: Optional[int] = None
    auth_type: str = Field(default="api_key")
    expires_at: Optional[datetime] = None


class RepositoryCreate(BaseModel):
    """Repository creation request"""

    owner_id: str
    owner_type: str = Field(..., pattern="^(internal|external)$")
    name: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    repo_type: str = Field(..., pattern="^(psychology|stock|ai|translation|vision|custom)$")
    protocol: str = Field(..., pattern="^(http|grpc|websocket)$")
    endpoint_url: Optional[str] = None
    config: Optional[Dict[str, Any]] = {}
    pricing_type: str = Field(default="per_call")
    price_per_call: Optional[float] = None
    price_per_token: Optional[float] = None
    monthly_price: Optional[float] = None
    free_calls: int = 0
    free_tokens: int = 0


class RepositoryUpdate(BaseModel):
    """Repository update request"""

    display_name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    endpoint_url: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, pattern="^(pending|approved|rejected|online|offline)$")


class RepositoryApproval(BaseModel):
    """Repository approval request"""

    comment: Optional[str] = None


class BillRecharge(BaseModel):
    """Bill recharge request"""

    user_id: str
    amount: float = Field(..., gt=0)
    payment_method: str = Field(default="admin")
    remark: Optional[str] = None


class ChatRequest(BaseModel):
    """Chat API request"""

    question: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None


class TranslateRequest(BaseModel):
    """Translation API request"""

    text: str = Field(..., min_length=1)
    source_lang: str = Field(default="auto")
    target_lang: str = Field(..., min_length=2, max_length=10)


class ImageRequest(BaseModel):
    """Image recognition API request"""

    image_url: Optional[str] = None
    image_data: Optional[str] = None  # Base64 encoded
    task: str = Field(default="ocr")
