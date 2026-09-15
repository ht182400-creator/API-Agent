"""
【一次性诊断脚本】路由挂载诊断。

背景：dump 路由快照时发现 `app.routes` 中看不到业务路由，
      与"pytest 269 全绿"矛盾 → 逐层打印路由数量与类型定位问题。
"""

import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s.%(msecs)03d] %(levelname)-5s %(name)s:%(lineno)d  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("diag_routes")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def main() -> int:
    from src.config import settings
    from src.api import api_router
    from src.api.v1 import api_router as v1_router
    from src.main import app

    logger.info("settings.api_v1_prefix = %r", getattr(settings, "api_v1_prefix", "<无此配置>"))
    logger.info("v1_router.routes  = %s", len(v1_router.routes))
    logger.info("api_router.routes = %s", len(api_router.routes))
    logger.info("app.routes        = %s", len(app.routes))

    logger.info("--- app.routes 明细（类型 + 路径）---")
    for route in app.routes:
        logger.info("  %-22s %s", type(route).__name__, getattr(route, "path", "?"))

    logger.info("--- v1_router.routes 前 10 条 ---")
    for route in v1_router.routes[:10]:
        logger.info("  %-22s %s", type(route).__name__, getattr(route, "path", "?"))

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 脚本级兜底
        import traceback

        logger.error("诊断异常: %s\n%s", exc, traceback.format_exc())
        sys.exit(2)
