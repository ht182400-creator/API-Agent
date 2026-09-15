"""
Environment helper - 账单/资金环境（simulation / production）统一解析

背景：
    平台同时存在"模拟支付"（测试）与"真实支付"（生产）两种运行态，
    账单表 `bills` 与月度账单表 `monthly_bills` 通过 `environment` 字段隔离两套数据。

设计目标：
    1. 环境口径唯一：写入与查询都走同一处逻辑，避免分散导致数据不一致。
    2. 默认安全：未显式指定时，默认只查询"当前环境"的数据。
    3. 可查历史：显式传 environment=all 时不做环境过滤，便于对账/排查。
    4. 非法值降级：非法环境值降级为当前环境并记录告警，避免异常与越权。

注意：
    本模块只负责"环境标识的解析"，不负责权限校验；
    调用方仍需保证查询条件已限定在用户/管理员可见范围内。
"""

from typing import Any, Optional

from src.config.logging_config import get_logger

logger = get_logger("environment")

# 合法的具体环境标识（不含 all 通配）
VALID_ENVIRONMENTS = ("simulation", "production")

# 通配值：表示"不做环境过滤"，即同时返回模拟与真实数据
ENVIRONMENT_ALL = "all"

# 当前环境的默认值（与 settings.billing_environment 保持一致，避免循环导入）
_DEFAULT_ENVIRONMENT = "simulation"


def current_environment() -> str:
    """
    返回当前运行环境对应的账单环境标识。

    - 生产环境（ENVIRONMENT=production/prod）→ "production"
    - 其余环境（development / staging / ...）→ "simulation"

    注意：本值由 `ENVIRONMENT` 决定，**与模拟支付开关 `PAYMENT_MOCK_MODE` 解耦**。
    """
    try:
        from src.config.settings import settings

        return settings.billing_environment
    except Exception:  # pragma: no cover - 极端情况下（配置未就绪）降级
        return _DEFAULT_ENVIRONMENT


def resolve_environment(environment: Optional[str]) -> str:
    """
    解析环境过滤参数。

    Args:
        environment: 前端传入的环境过滤值，可为 None / "simulation" / "production" / "all"

    Returns:
        "simulation" | "production" | "all"

    规则：
        - None / 空字符串 → 当前环境（默认，仅看当前态数据）
        - "all"           → 不做过滤，可同时查看模拟与真实数据
        - 合法具体值       → 原样返回
        - 非法值           → 降级为当前环境并记录告警
    """
    if environment is None or not str(environment).strip():
        return current_environment()

    value = str(environment).strip().lower()
    if value == ENVIRONMENT_ALL:
        return ENVIRONMENT_ALL
    if value in VALID_ENVIRONMENTS:
        return value

    logger.warning(
        "[Environment] 非法的环境过滤值 '%s'，已降级为当前环境 '%s'",
        environment,
        current_environment(),
    )
    return current_environment()


def env_match(column: Any, environment: str):
    """
    生成 SQLAlchemy 环境过滤条件。

    Args:
        column: 环境字段列，例如 Bill.environment
        environment: resolve_environment() 的返回值

    Returns:
        当 environment == "all" 时返回恒真条件（不过滤）；
        否则返回 column == environment。

    用法：
        environment = resolve_environment(environment)
        conditions = [Bill.user_id == current_user.id, env_match(Bill.environment, environment)]
    """
    from sqlalchemy import true

    if environment == ENVIRONMENT_ALL:
        return true()
    return column == environment
