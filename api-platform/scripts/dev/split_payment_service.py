"""
【一次性代码生成脚本】P1-4 巨型文件拆分 —— payment_service.py → payment/ 包。

背景：
    ``src/services/payment_service.py`` 共 1170 行 / 44KB，单文件承载了套餐管理、
    下单、支付宝对接、回调入账、查询列表等全部职责（违反「单文件 ≤500 行」约定）。

为什么用 **Mixin 组合** 而不是拆成多个独立类：
    原文件只有一个类 ``PaymentService``，方法之间大量互相调用（``self.xxx``）。
    拆成多个独立类必须改造这些调用关系（高风险）；用 Mixin 则**所有方法仍挂在同一个
    PaymentService 上**，``self.xxx`` 调用与外部 ``from ... import PaymentService``
    完全不变 —— 属于"纯搬移"，行为零改变（拆分后必须跑全量测试验证）。

产物：
    src/services/payment/
    ├── __init__.py       # re-export PaymentService（对外接口不变）
    ├── service.py        # 组合各 Mixin + __init__（注入 self.db）
    ├── _orders.py        # 单号生成 / 下单 / 取消 / 退款 / 自定义充值
    ├── _packages.py      # 充值套餐管理
    ├── _alipay.py        # 支付宝（当面付 / 二维码 / 交易查询 / 状态同步）
    ├── _callback.py      # 回调入账 / 余额更新 / 用户升级
    └── _query.py         # 支付查询 / 列表

用法（在 api-platform 目录下）：
    python scripts/dev/split_payment_service.py
"""

import ast
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

# 统一日志格式（毫秒级）
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s.%(msecs)03d] %(levelname)-5s %(name)s:%(lineno)d  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("split_payment")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SOURCE = _PROJECT_ROOT / "src" / "services" / "payment_service.py"
_TARGET_DIR = _PROJECT_ROOT / "src" / "services" / "payment"

# 分组定义：目标文件 → (Mixin 类名, 职责说明, 方法名列表)
# ⚠️ 必须覆盖源文件类内的**全部**方法，否则脚本报错退出（防止静默丢代码）
_GROUPS: Dict[str, Tuple[str, str, Sequence[str]]] = {
    "_orders.py": (
        "PaymentOrdersMixin",
        "支付/订单生命周期：单号生成、下单、支付链接、取消、退款、自定义充值",
        (
            "generate_payment_no",
            "generate_order_no",
            "create_payment",
            "_generate_payment_url",
            "cancel_payment",
            "refund_payment",
            "create_custom_recharge",
        ),
    ),
    "_packages.py": (
        "PaymentPackagesMixin",
        "充值套餐管理：套餐查询/创建、充值金额校验、默认套餐初始化",
        (
            "list_packages",
            "get_package",
            "create_package",
            "validate_recharge_amount",
            "init_default_packages",
        ),
    ),
    "_alipay.py": (
        "PaymentAlipayMixin",
        "支付宝对接：当面付下单、二维码生成/刷新、交易查询、支付状态同步",
        (
            "_generate_alipay_url",
            "_generate_alipay_qrcode",
            "generate_alipay_qrcode",
            "refresh_alipay_qrcode",
            "query_alipay_trade",
            "sync_payment_status_from_alipay",
        ),
    ),
    "_callback.py": (
        "PaymentCallbackMixin",
        "支付回调：回调入账（幂等）、余额更新、充值后用户升级",
        (
            "handle_payment_callback",
            "update_user_balance_after_payment",
            "_process_successful_payment",
            "_upgrade_user_after_recharge",
        ),
    ),
    "_query.py": (
        "PaymentQueryMixin",
        "支付查询：按支付单号/订单号查询、用户支付列表（分页）",
        (
            "query_payment",
            "query_payment_by_order",
            "list_user_payments",
        ),
    ),
}

# 按"实际用到的名字"筛选的 import 候选：template 的 import 目标会被替换成命中的名字
# （`import xxx` 形式原样输出；`from A import ...` 形式按命中名字重建）
_IMPORT_CANDIDATES: Sequence[Tuple[str, Sequence[str]]] = (
    ("import asyncio", ("asyncio",)),
    ("import uuid", ("uuid",)),
    ("import json", ("json",)),
    ("import hashlib", ("hashlib",)),
    ("import time", ("time",)),
    ("from typing import Any", ("Optional", "List", "Dict", "Any", "Tuple")),
    ("from datetime import Any", ("datetime", "timedelta", "timezone")),
    ("from sqlalchemy.ext.asyncio import Any", ("AsyncSession",)),
    ("from sqlalchemy import Any", ("select", "func", "and_", "or_")),
    ("from src.models.payment import Any", ("Payment", "RechargePackage")),
    ("from src.models.billing import Any", ("Account", "Bill")),
    (
        "from src.core.exceptions import Any",
        ("ValidationError", "NotFoundError", "PaymentError", "InvalidParameterError"),
    ),
)


def _used(body: str, name: str) -> bool:
    """判断方法体源码里是否用到了某个名字（词边界匹配，避免子串误判）"""
    return re.search(rf"\b{re.escape(name)}\b", body) is not None


def _build_imports(body: str) -> str:
    """按实际使用情况生成 Mixin 文件的 import 段（避免无用 import）"""
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

    # 去重（保持顺序）
    seen, unique = set(), []
    for line in out:
        if line not in seen:
            seen.add(line)
            unique.append(line)
    return "\n".join(unique)


def _collect_class_functions(lines: List[str]) -> Tuple[List[Tuple[str, int, int]], int]:
    """
    解析源文件，返回类内所有方法的 (名称, 起始行, 结束行) 与类体起始行（均为 1-based）。

    说明：起始行取 ``def`` 行（含装饰器时取最上面的装饰器行）；方法上方的注释/分组标题
    由 :func:`_extract_segment` 向前吞并。
    """
    tree = ast.parse("".join(lines))
    cls = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "PaymentService":
            cls = node
            break
    if cls is None:
        raise RuntimeError("未在源文件中找到 class PaymentService")

    body_start = cls.body[0].end_lineno  # 类 docstring 结束行
    funcs: List[Tuple[str, int, int]] = []
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            if node.decorator_list:
                start = min(start, min(d.lineno for d in node.decorator_list))
            funcs.append((node.name, start, node.end_lineno))
    return funcs, body_start


def _extract_segment(lines: List[str], start: int, end: int, body_start: int) -> str:
    """
    截取方法源码，并**向前吞掉紧邻的注释/空行**（分组标题、说明注释随方法一起搬走）。

    Args:
        start/end: 方法起止行号（1-based，含）
        body_start: 类 docstring 结束行号（吞并不得越过它）
    """
    idx = start - 1  # 0-based，指向方法首行
    while idx > body_start and (
        lines[idx - 1].lstrip().startswith("#") or not lines[idx - 1].strip()
    ):
        idx -= 1
    return "".join(lines[idx:end])


def main() -> int:
    if not _SOURCE.exists():
        logger.error("源文件不存在: %s", _SOURCE)
        return 1

    lines = _SOURCE.read_text(encoding="utf-8").splitlines(keepends=True)
    funcs, body_start = _collect_class_functions(lines)
    logger.info("解析完成：类内方法 %s 个，类体起始行 %s", len(funcs), body_start)

    # 覆盖性校验：分组必须恰好包含全部方法（缺失/多余/重复都视为脚本错误）
    grouped = [name for _, _, names in _GROUPS.values() for name in names]
    actual = {name for name, _, _ in funcs} - {"__init__"}
    missing = actual - set(grouped)
    unknown = set(grouped) - actual
    duplicated = {n for n in grouped if grouped.count(n) > 1}
    if missing or unknown or duplicated:
        logger.error("分组定义与源文件不一致：未分组=%s 不存在=%s 重复=%s", missing, unknown, duplicated)
        return 1

    _TARGET_DIR.mkdir(parents=True, exist_ok=True)

    for filename, (mixin_name, desc, methods) in _GROUPS.items():
        segments = [
            _extract_segment(lines, start, end, body_start)
            for name, start, end in funcs
            if name in methods
        ]
        group_body = "".join(segments).rstrip() + "\n"
        imports = _build_imports(group_body)

        content = (
            f'"""\n{desc}\n\n'
            f"由 `scripts/dev/split_payment_service.py` 从 `payment_service.py` 精确搬移生成，\n"
            f"方法体与原实现逐字一致（仅移动位置）。\n\n"
            f"⚠️ 依赖宿主类提供 ``self.db``（由 :class:`PaymentService` 组合）。\n"
            f'"""\n\n'
            f"{imports}\n"
            f"from src.config.logging_config import get_logger\n\n"
            f'logger = get_logger("payment")\n\n\n'
            f"class {mixin_name}:\n"
            f'    """{desc}"""\n\n'
            f"{group_body}"
        )
        (_TARGET_DIR / filename).write_text(content, encoding="utf-8")
        logger.info("已生成 %s（%s 个方法，%s 行）", filename, len(methods), len(content.splitlines()))

    # service.py：组合入口
    mixin_imports = "\n".join(
        f"from src.services.payment.{filename[:-3]} import {mixin_name}"
        for filename, (mixin_name, _, _) in _GROUPS.items()
    )
    service_py = (
        '"""\n支付服务 - 组合入口\n\n'
        "P1-4 拆分：原 1170 行的单文件按子域拆为同包内的多个 Mixin；\n"
        "本类只负责组合与 ``self.db`` 注入，各子域实现见同包 ``_*.py``。\n"
        '"""\n\n'
        "from sqlalchemy.ext.asyncio import AsyncSession\n\n"
        f"{mixin_imports}\n\n\n"
        "class PaymentService(\n"
        + "".join(f"    {mixin_name},\n" for _, (mixin_name, _, _) in _GROUPS.items())
        + "):\n"
        '    """支付服务 - 核心业务逻辑（各子域实现见同包 _*.py）"""\n\n'
        "    def __init__(self, db: AsyncSession):\n"
        "        self.db = db\n"
    )
    (_TARGET_DIR / "service.py").write_text(service_py, encoding="utf-8")
    logger.info("已生成 service.py（组合 %s 个 Mixin）", len(_GROUPS))

    # __init__.py：对外接口保持 from src.services.payment import PaymentService
    init_py = (
        '"""\n支付服务包\n\n'
        "P1-4 拆分产物：对外接口为 ``from src.services.payment import PaymentService``。\n"
        '"""\n\n'
        "from src.services.payment.service import PaymentService\n\n"
        '__all__ = ["PaymentService"]\n'
    )
    (_TARGET_DIR / "__init__.py").write_text(init_py, encoding="utf-8")
    logger.info("已生成 __init__.py")

    logger.info("生成完成。下一步：① py_compile ② 更新引用点 import ③ 删除旧文件 ④ 全量 pytest")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 脚本级兜底：打印完整堆栈便于定位
        import traceback

        logger.error("拆分脚本异常: %s\n%s", exc, traceback.format_exc())
        sys.exit(2)
