"""
【脚本】API 路由模块拆分（P1-4）—— 把单文件路由模块按子域拆成包（AST 精确搬移）。

设计要点（与 `split_payment_service.py` 同一思路）：
    1. 用 `ast` 定位每个顶层「函数 / 类」的字节区间（含其上方注释与装饰器），**逐字搬移**，
       保证"纯搬移、行为零改变"；不靠人肉复制，避免漏行/错位。
    2. 子模块的 import **按实际使用筛选**（检查成员体文本里是否出现该名字），避免无用 import。
    3. 分组定义必须**恰好覆盖**源文件全部顶层成员（含 Pydantic 模型），否则脚本报错退出 ——
       防止静默丢代码。
    4. 生成的包 `__init__.py` 汇总出一个同名 `router`，**include 顺序与源文件定义顺序一致**，
       因此在 `src/api/v1/__init__.py` 中的挂载方式（prefix/tags）完全不用改。

⚠️ 前置：目标包目录必须**不存在**（否则包会遮蔽同名模块，或产生新旧混存）。
   拆分后需手动删除源文件，并跑：
     ① 路由快照对比（`scripts/dev/dump_analytics_routes.py <file> <prefix>`）
     ② 全量 pytest

用法（在 api-platform 目录下）：
    python scripts/dev/split_api_router.py
（修改下方「配置区」即可复用于其它 API 模块）
"""

import ast
import logging
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s.%(msecs)03d] %(levelname)-5s %(name)s:%(lineno)d  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("split_api")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ============================== 配置区 ==============================
# 源文件（相对 api-platform）
_SOURCE_REL = "src/api/v1/billing.py"
# 目标包（相对 api-platform）
_TARGET_REL = "src/api/v1/billing"
# 包用途说明（写进生成的 docstring）
_PACKAGE_DESC = "计费接口"
# logger 名称（与原模块保持一致，避免日志通道变化）
_LOG_NAME = "billing"
# 原模块是否在文件级定义了 router = APIRouter()（billing 是；若子模块自带 prefix 则改 False）
_ROUTER_HAS_PREFIX = False

# 共享成员（非端点）：放进 _shared.py
_SHARED_MEMBERS: Sequence[str] = ("_to_utc_iso_string",)

# 分组：目标文件 -> (职责说明, 成员名列表)。必须恰好覆盖源文件全部顶层成员。
_GROUPS: Dict[str, Tuple[str, Sequence[str]]] = {
    "account.py": ("账户信息与充值", ("get_account", "recharge")),
    "bills.py": ("账单查询与导出", ("get_bills", "export_bills")),
    "stats.py": ("账单统计与趋势", ("get_monthly_summary", "get_balance_history", "get_consumption_trend")),
    "usage.py": ("用量统计与消费明细", ("RepositoryUsageItem", "get_user_usage", "get_consumption_details")),
    "monthly.py": ("月度账单（列表 / 明细 / 可查周期）", ("get_my_monthly_bills", "get_my_monthly_bill_detail", "get_my_available_periods")),
}

# import 候选：(模板, 候选名字)。`import x` 形式原样输出；`from A import ...` 按命中名字重建。
_IMPORT_CANDIDATES: Sequence[Tuple[str, Sequence[str]]] = (
    ("from typing import Any", ("Optional", "List", "Dict", "Any", "Tuple")),
    ("from datetime import Any", ("datetime", "timezone", "timedelta")),
    ("from fastapi import Any", ("APIRouter", "Depends", "Query", "Body", "Path", "HTTPException", "Response")),
    ("from fastapi.responses import Any", ("StreamingResponse", "JSONResponse", "PlainTextResponse")),
    ("from sqlalchemy.ext.asyncio import Any", ("AsyncSession",)),
    ("from sqlalchemy import Any", ("select", "func", "desc", "asc", "and_", "or_", "Numeric", "DECIMAL", "text", "case")),
    ("from decimal import Any", ("Decimal",)),
    ("from pydantic import Any", ("BaseModel", "Field")),
    ("from src.config.database import Any", ("get_db",)),
    ("from src.config.logging_config import Any", ("get_logger",)),
    ("from src.schemas.response import Any", ("BaseResponse",)),
    ("from src.schemas.request import Any", ("BillRecharge",)),
    ("from src.services.auth_service import Any", ("get_current_user", "check_admin_permission")),
    ("from src.models.user import Any", ("User",)),
    ("from src.models.billing import Any", ("Account", "Bill", "APICallLog", "MonthlyBill")),
    ("from src.models.repository import Any", ("Repository", "RepoStats")),
    ("from src.core.exceptions import Any", ("APIError", "NotFoundError", "ValidationError", "AuthorizationError")),
    ("from src.utils.environment import Any", ("resolve_environment", "env_match", "current_environment")),
    ("from src.utils.time_range import Any", ("CST", "cst_now", "utc_now", "cst_date_str")),
)
# ====================================================================


def _used(body: str, name: str) -> bool:
    """成员体（含装饰器）里是否用到某个名字（词边界匹配）"""
    return re.search(rf"\b{re.escape(name)}\b", body) is not None


def _build_imports(body: str) -> str:
    """按实际使用生成 import 段"""
    out: List[str] = []
    for template, names in _IMPORT_CANDIDATES:
        hit = [name for name in names if _used(body, name)]
        if not hit:
            continue
        if template.startswith("import "):
            out.append(template)
        else:
            head = template.split(" import ")[0]
            out.append(f"{head} import {', '.join(hit)}")

    seen, unique = set(), []
    for line in out:
        if line not in seen:
            seen.add(line)
            unique.append(line)
    return "\n".join(unique)


def _ensure_import(imports: str, module: str, name: str) -> str:
    """
    确保 import 段包含 `from <module> import <name>`（已有同名行则并入该行）。

    为什么需要：文件头会固定引用 `APIRouter` / `get_logger`，而成员体里只出现
    `@router.xxx` / `logger.xxx` —— 按"使用情况筛选"必然漏掉这两个名字，
    导致生成代码在**运行期** NameError（编译期不报）。
    """
    lines = imports.split("\n") if imports else []
    prefix = f"from {module} import "
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            names = [item.strip() for item in line[len(prefix):].split(",")]
            if name not in names:
                names.append(name)
                lines[index] = prefix + ", ".join(names)
            return "\n".join(lines)

    lines.append(f"{prefix}{name}")
    return "\n".join(lines)


def _collect_members(lines: List[str]) -> Tuple[List[Tuple[str, int, int]], int]:
    """返回顶层成员 (名称, 起始行, 结束行) 与文件头结束行（import 段结束位置）"""
    tree = ast.parse("".join(lines))
    members: List[Tuple[str, int, int]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno
            if getattr(node, "decorator_list", None):
                start = min(start, min(d.lineno for d in node.decorator_list))
            members.append((node.name, start, node.end_lineno))
    return members, 0


def _extract_segment(lines: List[str], start: int, end: int, floor: int) -> str:
    """截取成员源码，并向前吞掉紧邻的注释/空行（分组标题随之搬走）；floor 为下界（1-based）"""
    idx = start - 1
    while idx > floor and (lines[idx - 1].lstrip().startswith("#") or not lines[idx - 1].strip()):
        idx -= 1
    return "".join(lines[idx:end])


def main() -> int:
    source = _PROJECT_ROOT / _SOURCE_REL
    target_dir = _PROJECT_ROOT / _TARGET_REL

    if not source.exists():
        logger.error("源文件不存在: %s", source)
        return 1
    if target_dir.exists():
        if "--force" not in sys.argv:
            logger.error("目标包已存在（会遮蔽同名模块）：%s —— 请先确认并清理，或加 --force", target_dir)
            return 1
        shutil.rmtree(target_dir)
        logger.warning("--force：已清空已存在的目标包 %s", target_dir)

    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    members, _ = _collect_members(lines)
    member_names = [name for name, _, _ in members]
    logger.info("解析完成：顶层成员 %s 个 -> %s", len(members), member_names)

    # 覆盖性校验：分组 + 共享成员 必须恰好等于源文件全部顶层成员
    declared = [name for _, names in _GROUPS.values() for name in names] + list(_SHARED_MEMBERS)
    missing = set(member_names) - set(declared)
    unknown = set(declared) - set(member_names)
    duplicated = {n for n in declared if declared.count(n) > 1}
    if missing or unknown or duplicated:
        logger.error("分组定义与源文件不一致：未分组=%s 不存在=%s 重复=%s", missing, unknown, duplicated)
        return 1

    target_dir.mkdir(parents=True, exist_ok=True)
    member_index = {name: (start, end) for name, start, end in members}
    floor = 1  # 注释吞并下界（文件首行）

    def render(file_desc: str, names: Sequence[str], *, is_shared: bool) -> str:
        segments = []
        for member_name, start, end in members:  # 按源码顺序，保证注释归属正确
            if member_name not in names:
                continue
            segments.append(_extract_segment(lines, start, end, floor))
        body = "".join(segments).rstrip() + "\n"

        imports = _build_imports(body)
        # ⚠️ 文件头固定引用 APIRouter / get_logger（成员体里只有 @router.xxx / logger.xxx），
        #    按使用情况筛选必然漏掉这两个名字 → 显式补齐；否则运行期 NameError（编译期不报）。
        imports = _ensure_import(imports, "src.config.logging_config", "get_logger")
        if not is_shared:
            imports = _ensure_import(imports, "fastapi", "APIRouter")

        extra_import = ""
        if (not is_shared) and _used(body, "_to_utc_iso_string"):
            extra_import = f"from src.api.v1.{Path(_TARGET_REL).name}._shared import _to_utc_iso_string"

        header_parts = [
            f'"""\n{file_desc}\n\n由 `scripts/dev/split_api_router.py` 从 `{_SOURCE_REL}` 精确搬移生成，\n'
            f"函数体与原实现逐字一致（仅移动位置）。\n\"\"\"\n"
        ]
        if imports:
            header_parts.append(f"\n{imports}\n")
        if extra_import:
            header_parts.append(f"{extra_import}\n")
        header_parts.append(f'\nlogger = get_logger("{_LOG_NAME}")\n')
        if not is_shared:
            header_parts.append("\nrouter = APIRouter()\n")
        header_parts.append("\n\n")
        return "".join(header_parts) + body

    # 1) _shared.py
    shared_body = render(f"{_PACKAGE_DESC} —— 共享辅助（`{_SOURCE_REL}` 拆分产物）", list(_SHARED_MEMBERS), is_shared=True)
    (target_dir / "_shared.py").write_text(shared_body, encoding="utf-8")
    logger.info("已生成 _shared.py")

    # 2) 各子模块
    for filename, (desc, names) in _GROUPS.items():
        content = render(f"{_PACKAGE_DESC} —— {desc}", names, is_shared=False)
        (target_dir / filename).write_text(content, encoding="utf-8")
        logger.info("已生成 %s（%s 个成员，%s 行）", filename, len(names), len(content.splitlines()))

    # 3) __init__.py（汇总 router，include 顺序 = 源文件定义顺序）
    pkg_name = Path(_TARGET_REL).name
    module_names = [filename[:-3] for filename in _GROUPS]
    imports = "\n".join(f"from src.api.v1.{pkg_name} import {name}" for name in module_names)
    prefix_arg = ", prefix=\"\"" if _ROUTER_HAS_PREFIX else ""
    includes = "\n".join(f"router.include_router({name}.router)" for name in module_names)
    init_py = (
        f'"""\n{_PACKAGE_DESC}（P1-4 拆分产物）\n\n'
        f"原单文件 `{_SOURCE_REL}` 按子域拆分为同包内的多个子路由模块；本文件只负责**汇总**，\n"
        f"对外仍导出唯一的 `router`（挂载方式与拆分前完全一致，`src/api/v1/__init__.py` 无需改动）。\n\n"
        f"⚠️ 子路由 include 顺序**刻意与拆分前的定义顺序保持一致**，避免路由匹配顺序变化；\n"
        f"拆分等价性由 `scripts/dev/dump_analytics_routes.py` 的路由快照比对验证。\n\"\"\"\n\n"
        f"from fastapi import APIRouter\n\n{imports}\n\n"
        f"router = APIRouter(){prefix_arg}\n\n{includes}\n\n__all__ = [\"router\"]\n"
    )
    (target_dir / "__init__.py").write_text(init_py, encoding="utf-8")
    logger.info("已生成 __init__.py（汇总 %s 个子模块）", len(module_names))

    logger.info("生成完成。下一步：① 删除源文件 ② 编译 ③ 路由快照对比 ④ 全量 pytest")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 脚本级兜底
        import traceback

        logger.error("拆分脚本异常: %s\n%s", exc, traceback.format_exc())
        sys.exit(2)
