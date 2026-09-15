"""
【一次性校验脚本】验证 payment_service.py → payment/ 包的拆分是"纯搬移"。

为什么要做这层校验：
    拆分最大的风险是"搬移过程中悄悄改动了方法体"（漏行、错位、缩进变化）。
    仅靠编译和测试通过**不足以**证明零改变（未覆盖的分支可能被改坏）。
    本脚本用 ``ast.unparse`` 对每个方法做**结构化比较**：
    忽略空白/注释差异，只要 AST 不同就报差异 —— 覆盖全部 26 个方法。

对比对象：
    旧：`%TEMP%/payment_service.py.bak`（拆分前的备份）
    新：src/services/payment/*.py

用法（在 api-platform 目录下）：
    python scripts/dev/verify_payment_split.py
退出码：0 = 全部一致；1 = 存在差异；2 = 脚本异常
"""

import ast
import difflib
import logging
import sys
from pathlib import Path
from typing import Dict

# 允许以 `python scripts/dev/xxx.py` 方式直接运行（否则 sys.path[0] 是脚本目录，导不到 src）
_PROJECT_ROOT_EARLY = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT_EARLY) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT_EARLY))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s.%(msecs)03d] %(levelname)-5s %(name)s:%(lineno)d  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("verify_split")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_BACKUP = Path.home().joinpath("AppData", "Local", "Temp", "payment_service.py.bak")
_NEW_PACKAGE = _PROJECT_ROOT / "src" / "services" / "payment"


def _collect_methods(path: Path) -> Dict[str, str]:
    """提取文件内所有函数/方法的 AST 规范化文本（忽略格式差异）"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    methods: Dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in methods:
                logger.warning("同名方法重复出现（后者覆盖前者）: %s @ %s", node.name, path.name)
            methods[node.name] = ast.unparse(node)
    return methods


def main() -> int:
    if not _BACKUP.exists():
        logger.error("找不到拆分前备份: %s（请先执行拆分脚本时的备份步骤）", _BACKUP)
        return 1

    old = _collect_methods(_BACKUP)
    new: Dict[str, str] = {}
    sources: Dict[str, str] = {}
    for py_file in sorted(_NEW_PACKAGE.glob("*.py")):
        for name, body in _collect_methods(py_file).items():
            new[name] = body
            sources[name] = py_file.name

    logger.info("旧实现方法数=%s，新实现方法数=%s", len(old), len(new))

    missing = set(old) - set(new)
    extra = set(new) - set(old)
    if missing:
        logger.error("新实现缺失方法: %s", sorted(missing))
    if extra:
        logger.error("新实现多出方法: %s", sorted(extra))

    diffs = 0
    for name in sorted(set(old) & set(new)):
        if old[name] != new[name]:
            diffs += 1
            logger.error("方法体不一致: %s（新位置 %s）", name, sources.get(name, "?"))
            for line in difflib.unified_diff(
                old[name].splitlines(), new[name].splitlines(),
                fromfile=f"old:{name}", tofile=f"new:{name}", lineterm="",
            ):
                logger.error("    %s", line)

    # 补充校验：组合类上每个方法都必须可访问（Mixin 继承链正确、无遗漏、无意外覆盖）
    try:
        from src.services.payment import PaymentService

        unreachable = [name for name in old if not hasattr(PaymentService, name)]
        overridden = [
            name for name in old
            if name in PaymentService.__dict__ and name != "__init__"
        ]
    except Exception as exc:  # noqa: BLE001 导入失败即视为校验不通过
        logger.error("导入 PaymentService 失败: %s", exc)
        return 1

    if unreachable:
        logger.error("以下方法在组合类上不可访问（Mixin 继承链异常）: %s", sorted(unreachable))
    if overridden:
        logger.error("以下方法被组合类自身覆盖（应只在 Mixin 中定义）: %s", sorted(overridden))

    if missing or extra or diffs or unreachable or overridden:
        logger.error(
            "校验未通过：缺失=%s 多出=%s 内容差异=%s 不可访问=%s 被覆盖=%s",
            len(missing), len(extra), diffs, len(unreachable), len(overridden),
        )
        return 1

    logger.info("校验通过：%s 个方法的 AST 与拆分前完全一致（纯搬移，语义零改变）", len(old))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 脚本级兜底
        import traceback

        logger.error("校验脚本异常: %s\n%s", exc, traceback.format_exc())
        sys.exit(2)
