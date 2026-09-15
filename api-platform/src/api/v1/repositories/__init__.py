"""
仓库接口（P1-4 拆分产物）

原单文件 `src/api/v1/repositories.py` 按子域拆分为同包内的多个子路由模块；本文件只负责**汇总**，
对外仍导出唯一的 `router`（挂载方式与拆分前完全一致，`src/api/v1/__init__.py` 无需改动）。

⚠️ 子路由 include 顺序**刻意与拆分前的定义顺序保持一致**，避免路由匹配顺序变化；
含 catch-all 兜底路由的子模块（如 `proxy.py`）必须放在最后。
拆分等价性由 `scripts/dev/dump_analytics_routes.py` 的路由快照比对验证。
"""

from fastapi import APIRouter

from src.api.v1.repositories import catalog
from src.api.v1.repositories import invoke
from src.api.v1.repositories import crud
from src.api.v1.repositories import admin
from src.api.v1.repositories import endpoints
from src.api.v1.repositories import limits
from src.api.v1.repositories import config
from src.api.v1.repositories import proxy

# 兼容导出：拆包前这些符号位于模块顶层，既有引用（如测试直接 import 内部函数）
# 仍从包根导入，故在此 re-export，避免破坏既有 import 语句。
from src.api.v1.repositories._shared import _validate_endpoint_url, calculate_and_charge
from src.services.auth_service import get_current_user, check_admin_permission

router = APIRouter()

router.include_router(catalog.router, prefix="/repositories")
router.include_router(invoke.router, prefix="/repositories")
router.include_router(crud.router, prefix="/repositories")
router.include_router(admin.router, prefix="/repositories")
router.include_router(endpoints.router, prefix="/repositories")
router.include_router(limits.router, prefix="/repositories")
router.include_router(config.router, prefix="/repositories")
router.include_router(proxy.router, prefix="/repositories")

__all__ = ["router", "_validate_endpoint_url", "calculate_and_charge", "get_current_user", "check_admin_permission"]
