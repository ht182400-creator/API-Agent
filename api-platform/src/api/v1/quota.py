"""Quota API - 配额接口"""

from fastapi import APIRouter, Header

from src.schemas.response import BaseResponse, QuotaResponse, QuotaDetailResponse, BalanceResponse

router = APIRouter()


@router.get("", response_model=BaseResponse[QuotaResponse])
async def get_quota(
    x_access_key: str = Header(..., description="API Access Key"),
    x_signature: str = Header(..., description="HMAC Signature"),
    x_timestamp: str = Header(..., description="Request timestamp"),
    x_nonce: str = Header(..., description="Request nonce"),
):
    """
    Get current quota usage
    
    Returns quota information including rate limits and balance.
    """
    # In production, this would:
    # 1. Verify the API key
    # 2. Query quota usage from database/Redis
    # 3. Return current quota status
    
    # Placeholder response
    import time
    
    return BaseResponse(
        data=QuotaResponse(
            rpm=QuotaDetailResponse(
                limit=1000,
                used=150,
                remaining=850,
                reset_at=int(time.time()) + 60,
            ),
            rph=QuotaDetailResponse(
                limit=10000,
                used=5000,
                remaining=5000,
                reset_at=int(time.time()) + 3600,
            ),
            daily=QuotaDetailResponse(
                limit=100000,
                used=50000,
                remaining=50000,
                reset_at=int(time.time()) + 86400,
            ),
            balance=BalanceResponse(
                amount=100.00,
                currency="CNY",
            ),
        )
    )
