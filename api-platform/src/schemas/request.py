"""Request schemas - 请求模型"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """User creation request"""

    username: Optional[str] = Field(None, min_length=3, max_length=50)  # 用户名（可选，唯一）
    email: EmailStr
    password: str = Field(..., min_length=8)
    user_type: str = Field(default="developer")
    role: str = Field(default="user")  # 角色
    nickname: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # 用户名只能是字母、数字、下划线，3-50个字符
            import re
            if not re.match(r'^[a-zA-Z0-9_]{3,50}$', v):
                raise ValueError("用户名只能是字母、数字、下划线，3-50个字符")
        return v


class UserLogin(BaseModel):
    """User login request"""

    username: Optional[str] = Field(None, description="用户名（与 email 二选一）")
    email: Optional[str] = Field(None, description="邮箱（与 username 二选一）")
    password: str

    @field_validator("username", "email")
    @classmethod
    def validate_login_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            if len(v) < 3:
                raise ValueError("用户名/邮箱至少3个字符")
        return v

    def model_post_init(self, __context: Any) -> None:
        # 确保 username 或 email 至少有一个
        if not self.username and not self.email:
            raise ValueError("用户名或邮箱至少填写一个")


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


# 别名：前端使用的名称
CreateAPIKeyRequest = APIKeyCreate


class RepositoryCreate(BaseModel):
    """Repository creation request"""

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
    repo_type: Optional[str] = Field(None, pattern="^(psychology|stock|ai|translation|vision|custom)$")
    status: Optional[str] = Field(None, pattern="^(pending|approved|rejected|online|offline)$")


class RepositoryApproval(BaseModel):
    """Repository approval request"""

    comment: Optional[str] = None


class RepositoryReject(BaseModel):
    """Repository rejection request"""

    reason: Optional[str] = Field(None, max_length=500)


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


# 别名：前端使用的名称
RechargeRequest = BillRecharge
