"""Services module - 业务逻辑服务

⚠️ 2026-09-15 清理：已移除死代码导出
    - ``RepoService``（0 处实例化，被 api/v1/repositories.py 的实际实现取代，已删除）
    - ``BillingService``（0 处实例化，计费统一由 AccountService 负责，类已删除；
      ``billing_service.generate_bill_no`` 仍为活代码，请按需显式 import）
"""

from .auth_service import AuthService
from .quota_service import QuotaService

__all__ = [
    "AuthService",
    "QuotaService",
]
