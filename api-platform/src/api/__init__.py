"""API module - API路由"""

from fastapi import APIRouter

from .v1 import api_router as v1_router
from .v1.admin_logs import router as admin_logs_router
from .v1.analytics import router as analytics_router

api_router = APIRouter()
api_router.include_router(v1_router, tags=["v1"])
api_router.include_router(admin_logs_router, tags=["admin-logs"])
api_router.include_router(analytics_router, tags=["analytics"])

__all__ = ["api_router"]
