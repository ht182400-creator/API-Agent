"""
计费接口 —— 共享辅助（`src/api/v1/billing.py` 拆分产物）

由 `scripts/dev/split_api_router.py` 从 `src/api/v1/billing.py` 精确搬移生成，
函数体与原实现逐字一致（仅移动位置）。
"""

from typing import Optional
from datetime import datetime, timezone
from src.config.logging_config import get_logger

logger = get_logger("billing")




def _to_utc_iso_string(dt: datetime) -> Optional[str]:
    """
    将 datetime 转换为 UTC ISO 格式字符串
    数据库存储的是 UTC 时间，直接转换为 UTC ISO 格式
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # naive datetime，假定为 UTC（数据库存储的就是 UTC 时间）
        return dt.replace(tzinfo=timezone.utc).isoformat()
    # aware datetime，直接转换为 UTC
    return dt.astimezone(timezone.utc).isoformat()
