"""
【一次性验证脚本】导出路由表快照（默认 `/api/v1/analytics*`），用于拆分前后零回归比对。

⚠️ 实现要点（踩坑记录）：
    不能遍历 `app.routes` 取路径 —— 当前 FastAPI 版本的 `include_router` 生成的是
    **惰性 `_IncludedRouter` 对象**（不含子路由明细），`app.routes` 里看不到业务路径
    （实测只有 openapi/docs/health/ready 等 8 条，容易误判为"路由丢了"）。
    正确做法：用 **OpenAPI schema**（`app.openapi()["paths"]`）取全量路径 —— 与运行时路由一致。

用法（在 api-platform 目录下）：
    python scripts/dev/dump_analytics_routes.py before.json
    python scripts/dev/dump_analytics_routes.py after.json
    python scripts/dev/dump_analytics_routes.py all.json /api/v1        # 自定义前缀
    # 比对：Compare-Object (Get-Content before.json) (Get-Content after.json)
"""

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s.%(msecs)03d] %(levelname)-5s %(name)s:%(lineno)d  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("dump_routes")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_DEFAULT_PREFIX = "/api/v1/analytics"

# OpenAPI schema 中除 HTTP 方法外的键（如 parameters / summary）
_HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options", "trace"}


def main() -> int:
    from src.main import app

    if len(sys.argv) < 2:
        logger.error("用法: python scripts/dev/dump_analytics_routes.py <输出文件> [路径前缀]")
        return 1

    target = Path(sys.argv[1])
    prefix = sys.argv[2] if len(sys.argv) > 2 else _DEFAULT_PREFIX

    schema = app.openapi()
    all_paths = schema.get("paths", {})

    rows = []
    for path, operations in all_paths.items():
        if not path.startswith(prefix):
            continue
        methods = sorted(
            key.upper() for key in operations.keys() if key.lower() in _HTTP_METHODS
        )
        rows.append({"path": path, "methods": methods})

    rows.sort(key=lambda item: item["path"])
    target.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("前缀=%s 匹配到 %s 条路由（应用共 %s 条路径）-> %s", prefix, len(rows), len(all_paths), target)

    if not rows:
        logger.warning("未匹配到任何路由，以下为应用内全部路径：")
        for path in all_paths:
            logger.warning("  %s", path)
        return 1

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 脚本级兜底
        import traceback

        logger.error("导出路由快照异常: %s\n%s", exc, traceback.format_exc())
        sys.exit(2)
