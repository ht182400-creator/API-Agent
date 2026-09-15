"""
【脚本】API 路由模块拆分（P1-4）—— 把单文件路由模块按子域拆成包（AST 精确搬移）。

设计要点（与 `split_payment_service.py` 同一思路）：
    1. 用 `ast` 定位每个顶层「函数 / 类」的字节区间（含其上方注释与装饰器），**逐字搬移**，
       保证"纯搬移、行为零改变"；不靠人肉复制，避免漏行/错位。
    2. 子模块的 import **从源文件顶层 import 自动派生**并按实际使用筛选
       （手工维护候选清单必然遗漏 —— 实测：`RepositoryCreate` 只出现在类型注解里，
       漏 import 后编译期不报、运行期 NameError）。此外生成后会跑「未定义名字」自检兜底。
    3. 分组定义必须**恰好覆盖**源文件全部顶层成员，否则脚本报错退出 —— 防止静默丢代码。
    4. 生成的包 `__init__.py` 汇总出一个同名 `router`，**include 顺序与源文件定义顺序一致**
       （有自检），因此在 `src/api/v1/__init__.py` 中的挂载方式（prefix/tags）完全不用改。

⚠️ 路由顺序是硬约束：`__init__.py` 的 include 顺序 = `_GROUPS` 的书写顺序。
   若源文件含 **catch-all 兜底路由**（如 `@router.api_route("/{slug}/{path:path}")`），
   它必须位于 `_GROUPS` **最后一项**，否则会抢先匹配掉后面注册的静态路径路由。
   拆分前请用 `scripts/dev/dump_analytics_routes.py <文件> <前缀>` 取快照，拆分后逐条比对。

⚠️ 前置：目标包目录必须**不存在**（否则包会遮蔽同名模块，或产生新旧混存）。
   拆分后需手动删除源文件，并跑：
     ① 路由快照对比（`scripts/dev/dump_analytics_routes.py <file> <prefix>`）
     ② 全量 pytest

用法（在 api-platform 目录下）：
    python scripts/dev/split_api_router.py
（修改下方「配置区」即可复用于其它 API 模块；已实践：analytics / billing / repositories）
"""

import ast
import builtins
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
_SOURCE_REL = "src/api/v1/repositories.py"
# 目标包（相对 api-platform）
_TARGET_REL = "src/api/v1/repositories"
# 包用途说明（写进生成的 docstring）
_PACKAGE_DESC = "仓库接口"
# logger 名称（与原模块保持一致，避免日志通道变化）
_LOG_NAME = "repositories"
# 原模块是否定义了**模块级 logger**；False 则不生成 logger 行（避免无用 import 触发 lint）
_NEEDS_LOGGER = False
# 中间层 router（包 __init__.py）的 prefix：
#   ⚠️ 若源文件含**空路径路由**（如 `@router.get("")`），中间层 router 必须持**非空 prefix**，
#      否则 `include_router` 会抛 "Prefix and path cannot be both empty"
#      （FastAPI 拒绝"空 prefix + 空 path"的组合）。
#   ⚠️ 设置后必须把 `src/api/v1/__init__.py` 中挂载时的 `prefix=` 参数**去掉**（否则双重前缀）。
_PACKAGE_PREFIX = "/repositories"

# 共享成员（非端点）：放进 _shared.py；子模块若用到会自动补 import
_SHARED_MEMBERS: Sequence[str] = (
    "_validate_endpoint_url",
    "calculate_and_charge",
    # `_check_repo_update_permission` 已删除（P1-4 拆分时清理的死代码：全项目 0 调用，
    #   且函数体内使用未导入的 timedelta / db —— 由本脚本的未绑定名字自检暴露）。
    "_check_repo_owner_permission",
    "_get_repo_by_id",
)

# 兼容导出：拆包后仍需从**包根**导入的符号（既有测试/其它模块可能直接引用内部函数）
#   格式：(子模块文件名去后缀, 符号名列表)；写进 __init__.py 的 re-export，避免破坏既有 import。
_COMPAT_EXPORTS: Sequence[Tuple[str, Sequence[str]]] = (
    # 包内子模块（不含 "."）→ 从 `src.api.v1.<pkg>.<stem>` re-export
    ("_shared", ("_validate_endpoint_url", "calculate_and_charge")),
    # 外部模块（含 "."）→ 原样 `from <module> import ...`
    #   源文件顶部的 import 会让这些名字**在模块级别可访问**
    #   （如测试里的 `src.api.v1.repositories.check_admin_permission`，用于断言权限实现唯一），
    #   拆包后这些名字散落到各子模块 → 必须在包根补回，否则破坏既有引用。
    ("src.services.auth_service", ("get_current_user", "check_admin_permission")),
)

# 分组：目标文件 -> (职责说明, 成员名列表)。必须恰好覆盖源文件全部顶层成员。
#   ⚠️ 顺序即路由注册顺序；catch-all 兜底路由所在文件必须放在最后。
_GROUPS: Dict[str, Tuple[str, Sequence[str]]] = {
    "catalog.py": (
        "仓库列表与详情",
        ("list_repositories", "list_my_repositories", "get_repository_stats", "get_repository"),
    ),
    "invoke.py": (
        "仓库能力调用（对话 / 翻译 / 识别）",
        ("chat", "translate", "recognize"),
    ),
    "crud.py": (
        "仓库创建 / 更新 / 删除",
        ("create_repository", "update_repository", "delete_repository"),
    ),
    "admin.py": (
        "管理员仓库列表与审核（通过 / 驳回 / 上线 / 下线）",
        (
            "list_all_repositories_for_admin",
            "approve_repository",
            "reject_repository",
            "online_repository",
            "offline_repository",
        ),
    ),
    "endpoints.py": (
        "仓库端点配置（列表 / 增删改 / 批量）",
        (
            "list_endpoints",
            "create_endpoint",
            "update_endpoint",
            "delete_endpoint",
            "batch_update_endpoints",
        ),
    ),
    "limits.py": ("仓库限流配置", ("get_limits", "update_limits")),
    "config.py": ("仓库配置更新（端点 + 限流 + 定价一次性提交）", ("update_repository_config",)),
    "proxy.py": (
        "通用端点代理（catch-all 兜底路由，必须最后注册）",
        ("proxy_repository_endpoint",),
    ),
}
# ====================================================================

_BUILTIN_NAMES = set(dir(builtins))


def _used(body: str, name: str) -> bool:
    """成员体（含装饰器）里是否用到某个名字（词边界匹配）"""
    return re.search(rf"\b{re.escape(name)}\b", body) is not None


def _collect_import_candidates(lines: List[str]) -> List[Tuple[str, Sequence[str]]]:
    """
    从源文件**顶层 import** 自动派生候选清单（保持原顺序）。

    Returns:
        [(模板, 候选名字)]，模板形如 `from src.schemas.request import Any` / `import httpx`；
        `from X import ...` 的元素会让 `_build_imports` 按命中名字重建 import 行。
    """
    tree = ast.parse("".join(lines))
    candidates: List[Tuple[str, Sequence[str]]] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = tuple(alias.name for alias in node.names)
            if names:
                candidates.append((f"from {module} import Any", names))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                candidates.append((f"import {alias.name}", ()))
    return candidates


def _build_imports(body: str, candidates: Sequence[Tuple[str, Sequence[str]]]) -> str:
    """按实际使用生成 import 段（candidates 由源文件顶层 import 自动派生）"""
    out: List[str] = []
    for template, names in candidates:
        if template.startswith("import "):
            module_name = template[len("import "):]
            if _used(body, module_name.split(".")[0]):
                out.append(template)
            continue

        hit = [name for name in names if _used(body, name)]
        if not hit:
            continue
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


def _collect_stray_statements(lines: List[str]) -> List[str]:
    """
    列出顶层「既不是成员、又不是 import」的语句（docstring / router / logger 赋值除外）。

    ⚠️ 为什么要检查：拆分只搬移"函数 / 类"，而模块级**常量**（映射表、正则、配置字面量）
       不在其中，会被**静默丢弃** → 生成代码运行期 NameError。发现即报错，要求显式处置
       （把常量并入某个成员体内，或手工搬到 `_shared.py`）。
    """
    tree = ast.parse("".join(lines))
    keep = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)
    strays: List[str] = []
    for node in tree.body:
        if isinstance(node, keep):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue  # 模块 docstring / 裸字符串
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if targets in (["router"], ["logger"]):
                continue  # 由本脚本自行生成
        strays.append(f"L{node.lineno} {type(node).__name__}: {ast.unparse(node)[:80]}")
    return strays


def _extract_segment(lines: List[str], start: int, end: int, floor: int) -> str:
    """截取成员源码，并向前吞掉紧邻的注释/空行（分组标题随之搬走）；floor 为下界（1-based）"""
    idx = start - 1
    while idx > floor and (lines[idx - 1].lstrip().startswith("#") or not lines[idx - 1].strip()):
        idx -= 1
    return "".join(lines[idx:end])


def _iter_scope_nodes(stmts: Sequence[ast.stmt]):
    """
    遍历「当前作用域」内的节点：**不进入**嵌套函数 / 类体（但产出其定义节点，使函数名算作绑定）。

    ⚠️ 装饰器与默认值属于**外层**作用域，必须遍历（它们在外层求值）。
    """
    stack = list(stmts)
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for dec in getattr(node, "decorator_list", None) or []:
                stack.append(dec)
            args = getattr(node, "args", None)
            if args is not None:
                for default in list(args.defaults) + list(args.kw_defaults):
                    if default is not None:
                        stack.append(default)
            continue  # 不进入函数 / 类体（由递归单独分析）
        stack.extend(ast.iter_child_nodes(node))


def _bound_names(nodes: Sequence[ast.AST]) -> set:
    """收集节点集合中的绑定名（赋值目标 / import / 定义名 / except as 等）"""
    bound = set()
    for node in nodes:
        if isinstance(node, ast.Name):
            if not isinstance(node.ctx, ast.Load):
                bound.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            bound.update(node.names)
    return bound


def _scope_undefined(stmts: Sequence[ast.stmt], outer: set) -> set:
    """递归分析一个作用域：返回「被引用但未绑定」的名字集合（不含内建名）"""
    nodes = list(_iter_scope_nodes(stmts))
    bound = _bound_names(nodes) | outer
    referenced = {
        node.id for node in nodes if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    miss = referenced - bound - _BUILTIN_NAMES

    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            inner = set(bound)
            args = getattr(node, "args", None)
            if args is not None:
                for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
                    inner.add(arg.arg)
                if args.vararg:
                    inner.add(args.vararg.arg)
                if args.kwarg:
                    inner.add(args.kwarg.arg)
            miss |= _scope_undefined(node.body, inner)
    return miss


def _undefined_names(path: Path) -> List[str]:
    """
    列出文件中「被引用但未绑定」的名字 —— 用于发现拆分后漏掉的 import。

    实现是**作用域感知**的（模块 → 函数 → 嵌套函数逐层收集绑定），
    因此能正确识别「某函数内 import 了 X、另一函数却直接用 X」这类跨作用域缺陷
    （若改用"全文件绑定"近似，这种缺陷会被掩盖 —— 实测踩过）。

    ⚠️ 字符串形式的注解（`x: "Foo"`）不会被识别为引用 —— 属已知盲区（无法静态求值）。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    miss = _scope_undefined(tree.body, set())
    return sorted(name for name in miss if not name.startswith("__"))


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
    candidates = _collect_import_candidates(lines)
    logger.info("解析完成：顶层成员 %s 个 -> %s", len(members), member_names)
    logger.info("从源文件派生 import 候选 %s 组", len(candidates))

    # 覆盖性校验：分组 + 共享成员 必须恰好等于源文件全部顶层成员
    declared = [name for _, names in _GROUPS.values() for name in names] + list(_SHARED_MEMBERS)
    missing = set(member_names) - set(declared)
    unknown = set(declared) - set(member_names)
    duplicated = {n for n in declared if declared.count(n) > 1}
    if missing or unknown or duplicated:
        logger.error("分组定义与源文件不一致：未分组=%s 不存在=%s 重复=%s", missing, unknown, duplicated)
        return 1

    # 顺序自检：各分组「最小成员行号」必须单调递增，否则路由注册顺序会被打乱
    order = []
    for filename, (_, names) in _GROUPS.items():
        positions = [start for name, start, _ in members if name in names]
        if positions:
            order.append((filename, min(positions)))
    if order != sorted(order, key=lambda item: item[1]):
        logger.error("分组顺序与源码定义顺序不一致（会改变路由注册顺序）：%s", order)
        return 1
    logger.info("顺序自检通过（源码行号单调递增）：%s", order)

    # 模块级语句检查：拆分只搬移"函数 / 类"，如存在常量/映射表会被静默丢弃 → 发现即报错
    strays = _collect_stray_statements(lines)
    if strays:
        logger.error("源文件含模块级非成员语句（不会被搬移，会静默丢失）-> %s", strays)
        return 1
    logger.info("模块级语句检查通过：没有会被丢弃的常量 / 表达式")

    target_dir.mkdir(parents=True, exist_ok=True)
    floor = 1  # 注释吞并下界（文件首行）
    pkg_name = Path(_TARGET_REL).name

    def render(file_desc: str, names: Sequence[str], *, is_shared: bool) -> str:
        segments = []
        for member_name, start, end in members:  # 按源码顺序，保证注释归属正确
            if member_name not in names:
                continue
            segments.append(_extract_segment(lines, start, end, floor))
        body = "".join(segments).rstrip() + "\n"

        imports = _build_imports(body, candidates)
        # ⚠️ 文件头固定引用 APIRouter（成员体里只有 @router.xxx），按使用情况筛选必然漏掉
        #    → 显式补齐；否则运行期 NameError（编译期不报）。
        if _NEEDS_LOGGER:
            imports = _ensure_import(imports, "src.config.logging_config", "get_logger")
        if not is_shared:
            imports = _ensure_import(imports, "fastapi", "APIRouter")

        # 子模块若用到 _shared.py 的成员（成员体里只出现裸名字）→ 显式补 import
        extra_import = ""
        if not is_shared:
            shared_hits = [name for name in _SHARED_MEMBERS if _used(body, name)]
            if shared_hits:
                extra_import = (
                    f"from src.api.v1.{pkg_name}._shared import {', '.join(shared_hits)}"
                )

        header_parts = [
            f'"""\n{file_desc}\n\n由 `scripts/dev/split_api_router.py` 从 `{_SOURCE_REL}` 精确搬移生成，\n'
            f"函数体与原实现逐字一致（仅移动位置）。\n\"\"\"\n"
        ]
        if imports:
            header_parts.append(f"\n{imports}\n")
        if extra_import:
            header_parts.append(f"{extra_import}\n")
        if _NEEDS_LOGGER:
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
    module_names = [filename[:-3] for filename in _GROUPS]
    imports = "\n".join(f"from src.api.v1.{pkg_name} import {name}" for name in module_names)

    compat_imports = ""
    compat_names: List[str] = []
    if _COMPAT_EXPORTS:
        compat_lines = []
        for module_stem, names in _COMPAT_EXPORTS:
            # ⚠️ 变量名**不可**用 `source`：那会遮蔽 main() 里指向源文件的 Path（函数作用域），
            #    导致后续 `_undefined_names(source)` 收到 str 而 AttributeError。
            from_module = (
                module_stem
                if "." in module_stem
                else f"src.api.v1.{pkg_name}.{module_stem}"
            )
            compat_lines.append(f"from {from_module} import {', '.join(names)}")
            compat_names.extend(names)
        compat_imports = (
            "\n# 兼容导出：拆包前这些符号位于模块顶层，既有引用（如测试直接 import 内部函数）\n"
            "# 仍从包根导入，故在此 re-export，避免破坏既有 import 语句。\n"
            + "\n".join(compat_lines)
        )

    # ⚠️ prefix 必须加在 **include_router** 上，而不是给中间层 router 设 prefix：
    #    FastAPI 的空路径校验只看 `include_router(prefix)` 与**子路由原始 path**
    #    （子模块含 `@router.get("")`）→ 此处 prefix 为空即抛
    #    "Prefix and path cannot be both empty"（实测：中间层 router 带 prefix 也救不了）。
    _prefix_kw = f', prefix="{_PACKAGE_PREFIX}"' if _PACKAGE_PREFIX else ""
    includes = "\n".join(
        f"router.include_router({name}.router{_prefix_kw})" for name in module_names
    )
    all_names = '", "'.join(["router"] + compat_names)
    init_py = (
        f'"""\n{_PACKAGE_DESC}（P1-4 拆分产物）\n\n'
        f"原单文件 `{_SOURCE_REL}` 按子域拆分为同包内的多个子路由模块；本文件只负责**汇总**，\n"
        f"对外仍导出唯一的 `router`（挂载方式与拆分前完全一致，`src/api/v1/__init__.py` 无需改动）。\n\n"
        f"⚠️ 子路由 include 顺序**刻意与拆分前的定义顺序保持一致**，避免路由匹配顺序变化；\n"
        f"含 catch-all 兜底路由的子模块（如 `proxy.py`）必须放在最后。\n"
        f"拆分等价性由 `scripts/dev/dump_analytics_routes.py` 的路由快照比对验证。\n\"\"\"\n\n"
        f"from fastapi import APIRouter\n\n{imports}\n{compat_imports}\n\n"
        f"router = APIRouter()\n\n{includes}\n\n__all__ = [\"{all_names}\"]\n"
    )
    (target_dir / "__init__.py").write_text(init_py, encoding="utf-8")
    logger.info("已生成 __init__.py（汇总 %s 个子模块）", len(module_names))

    # 4) 自检：未绑定名字（捕捉"漏 import"——编译期不报、运行期才炸）
    #    基线豁免：源文件**本身**就存在的未绑定名字属既有缺陷（如死代码函数里用了未 import 的
    #    timedelta），拆分只是原样搬移、并未引入 → 不应阻断拆分；但要显式告警，避免被忽视。
    baseline = set(_undefined_names(source))
    if baseline:
        logger.warning(
            "注意：源文件本身存在未绑定名字（既有缺陷，非拆分引入，已豁免）-> %s", sorted(baseline)
        )

    problems = {}
    for path in sorted(target_dir.glob("*.py")):
        missed = [name for name in _undefined_names(path) if name not in baseline]
        if missed:
            problems[path.name] = missed
    if problems:
        logger.error("自检失败：以下文件存在【新增】未绑定名字（拆分引入的漏 import）-> %s", problems)
        return 1
    logger.info("import 自检通过：%s 个文件无新增未绑定名字", len(list(target_dir.glob("*.py"))))

    if _PACKAGE_PREFIX:
        logger.warning(
            "⚠️ 本包 router 自带 prefix=%s（源文件含空路径路由）→ 请确认 "
            "src/api/v1/__init__.py 挂载时**未再传 prefix**，否则路径变成双重前缀。",
            _PACKAGE_PREFIX,
        )
    logger.info("生成完成。下一步：① 删除源文件 ② 编译 ③ 路由快照对比 ④ 全量 pytest")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 脚本级兜底
        import traceback

        logger.error("拆分脚本异常: %s\n%s", exc, traceback.format_exc())
        sys.exit(2)
