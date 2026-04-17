"""Response schemas - 响应模型"""

from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime

from pydantic import BaseModel, Field


# Generic type for response data
T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Base API response"""

    code: int = 0
    message: str = "success"
    data: Optional[T] = None
    request_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "code": 0,
                "message": "success",
                "data": {},
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated API response"""

    items: List[T]
    pagination: Dict[str, Any] = Field(
        default_factory=lambda: {
            "page": 1,
            "page_size": 20,
            "total": 0,
            "total_pages": 0,
        }
    )


class ErrorResponse(BaseModel):
    """Error response"""

    code: int
    message: str
    request_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# User schemas
class UserResponse(BaseModel):
    """User response"""

    id: str
    email: str
    user_type: str
    user_status: str
    nickname: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserProfileResponse(BaseModel):
    """User profile response"""

    id: str
    user_id: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    real_name: Optional[str] = None
    company: Optional[str] = None
    created_at: datetime


# API Key schemas
class APIKeyResponse(BaseModel):
    """API Key response"""

    id: str
    key: Optional[str] = None  # Only returned on creation
    secret: Optional[str] = None  # Only returned on creation
    key_name: str
    key_prefix: str
    auth_type: str
    rate_limit_rpm: int
    daily_quota: Optional[int] = None
    monthly_quota: Optional[int] = None
    status: str
    expires_at: Optional[datetime] = None
    created_at: datetime
    total_calls: int = 0


class APIKeyListResponse(BaseModel):
    """API Key list response"""

    items: List[APIKeyResponse]
    pagination: Dict[str, Any]


# Repository schemas
class RepositoryOwnerResponse(BaseModel):
    """Repository owner response"""

    id: str
    name: str


class RepositoryPricingResponse(BaseModel):
    """Repository pricing response"""

    type: str
    price_per_call: Optional[float] = None
    price_per_token: Optional[float] = None
    monthly_price: Optional[float] = None
    free_calls: int = 0
    free_tokens: int = 0


class RepositoryLimitsResponse(BaseModel):
    """Repository limits response"""

    rpm: int
    rph: int
    daily: int


class RepositorySLAResponse(BaseModel):
    """Repository SLA response"""

    uptime: Optional[float] = None
    latency_p99: Optional[int] = None


class RepositoryEndpointResponse(BaseModel):
    """Repository endpoint response"""

    path: str
    method: str
    description: Optional[str] = None


class RepositoryResponse(BaseModel):
    """Repository response"""

    id: str
    name: str
    slug: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    type: str
    protocol: str
    status: str
    owner: Optional[RepositoryOwnerResponse] = None
    pricing: Optional[RepositoryPricingResponse] = None
    limits: Optional[RepositoryLimitsResponse] = None
    endpoints: List[RepositoryEndpointResponse] = []
    docs_url: Optional[str] = None
    sla: Optional[RepositorySLAResponse] = None
    created_at: datetime
    online_at: Optional[datetime] = None


class RepositoryListResponse(BaseModel):
    """Repository list response"""

    items: List[RepositoryResponse]
    pagination: Dict[str, Any]


# Quota schemas
class QuotaDetailResponse(BaseModel):
    """Quota detail response"""

    limit: int
    used: int
    remaining: int
    reset_at: Optional[int] = None


class BalanceResponse(BaseModel):
    """Balance response"""

    amount: float
    currency: str = "CNY"


class QuotaResponse(BaseModel):
    """Quota response"""

    rpm: QuotaDetailResponse
    rph: QuotaDetailResponse
    daily: QuotaDetailResponse
    balance: BalanceResponse


# Billing schemas
class BillResponse(BaseModel):
    """Bill response"""

    id: int
    bill_no: str
    bill_type: str
    amount: float
    balance_before: float
    balance_after: float
    description: Optional[str] = None
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None


class BillListResponse(BaseModel):
    """Bill list response"""

    items: List[BillResponse]
    pagination: Dict[str, Any]


# Statistics schemas
class UserStatsResponse(BaseModel):
    """User statistics response"""

    total: int
    developers: int
    owners: int


class RepositoryStatsResponse(BaseModel):
    """Repository statistics response"""

    total: int
    internal: int
    external: int
    online: int


class CallStatsResponse(BaseModel):
    """Call statistics response"""

    today: int
    this_month: int


class RevenueStatsResponse(BaseModel):
    """Revenue statistics response"""

    today: float
    this_month: float


class StatsOverviewResponse(BaseModel):
    """Statistics overview response"""

    users: UserStatsResponse
    repositories: RepositoryStatsResponse
    calls: CallStatsResponse
    revenue: RevenueStatsResponse


# Auth schemas
class TokenResponse(BaseModel):
    """Token response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class SignatureResponse(BaseModel):
    """Signature response"""

    signature: str
    timestamp: str
    nonce: str
    expires_at: int
