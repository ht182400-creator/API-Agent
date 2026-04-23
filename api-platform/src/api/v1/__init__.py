"""API v1 router"""

from fastapi import APIRouter

from .auth import router as auth_router
from .repositories import router as repositories_router
from .quota import router as quota_router
from .billing import router as billing_router
from .logs import router as logs_router
from .admin_logs import router as admin_logs_router
from .admin_users import router as admin_users_router
from .notifications import router as notifications_router
from .analytics import router as analytics_router
from .superadmin import router as superadmin_router
from .admin import router as admin_router
from .payment import router as payment_router  # V2.5新增
from .admin_reconciliation import router as admin_reconciliation_router  # V2.6新增
from .admin_payment_config import router as admin_payment_config_router  # V2.6新增
from .admin_pricing_config import router as admin_pricing_config_router  # V2.7新增
from .admin_billing import router as admin_billing_router  # P4月度账单优化新增
from .user import router as user_router  # 用户升级与试用功能新增

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(repositories_router, prefix="/repositories", tags=["Repositories"])
api_router.include_router(quota_router, prefix="/quota", tags=["Quota"])
api_router.include_router(billing_router, prefix="/billing", tags=["Billing"])
api_router.include_router(payment_router, tags=["Payments"])  # V2.5新增 (payment_router 已有 /payments 前缀)
api_router.include_router(logs_router, prefix="/logs", tags=["Logs"])
api_router.include_router(admin_logs_router, prefix="/admin/logs", tags=["Admin Logs"])
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
api_router.include_router(admin_users_router, prefix="/admin", tags=["Admin Users"])
api_router.include_router(admin_reconciliation_router, tags=["Admin Reconciliation"])  # V2.6新增 (router已有 /admin 前缀)
api_router.include_router(admin_payment_config_router, prefix="/admin", tags=["Admin Payment Config"])  # V2.6新增
api_router.include_router(admin_pricing_config_router, prefix="/admin", tags=["Admin Pricing Config"])  # V2.7新增
api_router.include_router(admin_billing_router, prefix="/admin/billing", tags=["Admin Billing"])  # P4月度账单优化新增
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(analytics_router, prefix="", tags=["Analytics"])
api_router.include_router(superadmin_router, prefix="/superadmin", tags=["Super Admin"])
api_router.include_router(user_router, tags=["User"])  # 用户升级与试用 (router已有 /user 前缀)

__all__ = ["api_router"]
