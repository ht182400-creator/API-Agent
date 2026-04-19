"""API v1 router"""

from fastapi import APIRouter

from .auth import router as auth_router
from .repositories import router as repositories_router
from .quota import router as quota_router
from .billing import router as billing_router
from .logs import router as logs_router
from .admin_logs import router as admin_logs_router
from .notifications import router as notifications_router
from .analytics import router as analytics_router
from .superadmin import router as superadmin_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(repositories_router, prefix="/repositories", tags=["Repositories"])
api_router.include_router(quota_router, prefix="/quota", tags=["Quota"])
api_router.include_router(billing_router, prefix="/billing", tags=["Billing"])
api_router.include_router(logs_router, prefix="/logs", tags=["Logs"])
api_router.include_router(admin_logs_router, prefix="/admin/logs", tags=["Admin Logs"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(analytics_router, prefix="", tags=["Analytics"])
api_router.include_router(superadmin_router, prefix="/superadmin", tags=["Super Admin"])

__all__ = ["api_router"]
