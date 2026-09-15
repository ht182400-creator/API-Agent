"""
Analytics API - 分析报表接口（P1-4 拆分产物）

原单文件 `src/api/v1/analytics.py`（716 行）按端点职责拆分为同包内的多个子路由模块；
本文件只负责**汇总**，对外仍导出唯一的 `router`（挂载方式与拆分前完全一致）：

    src/api/v1/analytics/
    ├── _shared.py       # 共享：权限校验、可见范围、缓存作用域、常量
    ├── overview.py      # GET /overview
    ├── trend.py         # GET /trend
    ├── details.py       # GET /repo-details
    ├── repo_trend.py    # GET /repo/{repo_id}/trend
    └── ranking.py       # GET /user-ranking、GET /repo-ranking

⚠️ 子路由 include 顺序**刻意与拆分前的定义顺序保持一致**
（overview → trend → repo-details → repo/{id}/trend → user-ranking → repo-ranking），
避免路由匹配顺序发生变化；拆分等价性由 `scripts/dev/dump_analytics_routes.py` 的快照比对验证。
"""

from fastapi import APIRouter

from src.api.v1.analytics import details, overview, ranking, repo_trend, trend

# ⚠️ 必须保留该 re-export（看似未使用）：
#    原 `analytics.py` 从 auth_service 复用了 check_admin_permission（P1-3「权限校验唯一实现」的收敛结果），
#    `tests/test_url_safety.py::TC-PERM-001` 会断言
#    `src.api.v1.analytics.check_admin_permission is src.services.auth_service.check_admin_permission`。
#    拆分后若删掉，该守卫测试即失败 —— 即"模块属性层面也必须与拆分前一致"。
from src.services.auth_service import check_admin_permission  # noqa: F401

# 与拆分前一致的统一前缀与 OpenAPI 分组
_ANALYTICS_TAGS = ["Analytics - 分析报表"]

router = APIRouter(prefix="/analytics", tags=_ANALYTICS_TAGS)

router.include_router(overview.router, tags=_ANALYTICS_TAGS)
router.include_router(trend.router, tags=_ANALYTICS_TAGS)
router.include_router(details.router, tags=_ANALYTICS_TAGS)
router.include_router(repo_trend.router, tags=_ANALYTICS_TAGS)
router.include_router(ranking.router, tags=_ANALYTICS_TAGS)

__all__ = ["router"]
