"""
计费接口（P1-4 拆分产物）

原单文件 `src/api/v1/billing.py` 按子域拆分为同包内的多个子路由模块；本文件只负责**汇总**，
对外仍导出唯一的 `router`（挂载方式与拆分前完全一致，`src/api/v1/__init__.py` 无需改动）。

⚠️ 子路由 include 顺序**刻意与拆分前的定义顺序保持一致**，避免路由匹配顺序变化；
拆分等价性由 `scripts/dev/dump_analytics_routes.py` 的路由快照比对验证。
"""

from fastapi import APIRouter

from src.api.v1.billing import account
from src.api.v1.billing import bills
from src.api.v1.billing import stats
from src.api.v1.billing import usage
from src.api.v1.billing import monthly

router = APIRouter()

router.include_router(account.router)
router.include_router(bills.router)
router.include_router(stats.router)
router.include_router(usage.router)
router.include_router(monthly.router)

__all__ = ["router"]
