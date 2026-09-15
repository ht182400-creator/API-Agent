"""
业务时间范围工具 —— 「北京时间业务口径 ↔ UTC 存储」统一转换。

背景（重要）：
    1. 数据库时间列已统一为 ``TIMESTAMP WITH TIME ZONE``（内部按 UTC 存储）；
    2. 但"今日 / 本周 / 本月"等**业务口径**面向中国用户，
       应为**北京时间（Asia/Shanghai）自然日 / 自然月**；
    3. 若直接用 ``datetime.now()``（本地 naive）与 timestamptz 列比较，
       asyncpg 会按**会话时区**（本项目为 UTC）解释该 naive 值
       → **统计结果偏移 8 小时**（这正是 2026-09-15 本次修复的问题）。

约定（与 `docs/BUG_FIXES.md` 的账单日期过滤口径一致）：
    业务语义的日期时间均为**北京时间**；与数据库比较前必须转换为 **aware** 时间 ——
    aware 值不受会话时区影响，asyncpg 会正确按 UTC 比较。

用法：
    from datetime import timedelta
    from src.utils.time_range import cst_now, cst_day_range_utc

    # 1) 相对时间（可直接与 timestamptz 比较）
    conditions.append(APICallLog.created_at >= cst_now() - timedelta(days=7))

    # 2) "今天"：建议用半开区间，而非 func.date(col) == ...
    start, end = cst_day_range_utc()
    conditions.append(APICallLog.created_at >= start)
    conditions.append(APICallLog.created_at < end)
"""

from datetime import date, datetime, timedelta, timezone
from typing import Tuple
from zoneinfo import ZoneInfo

# 业务时区（中国标准时间）
CST = ZoneInfo("Asia/Shanghai")


def cst_now() -> datetime:
    """当前北京时间（aware，tzinfo=Asia/Shanghai）"""
    return datetime.now(CST)


def utc_now() -> datetime:
    """
    当前 UTC 时间（aware）。

    用于响应中的 ``generated_at`` 等**输出字段**（前端会按本地时区展示）。
    """
    return datetime.now(timezone.utc)


def cst_day_start_utc(days_ago: int = 0) -> datetime:
    """
    北京时间「N 天前的 00:00」对应的 **UTC** 时刻（aware）。

    Args:
        days_ago: 0 = 今天，1 = 昨天，依此类推
    """
    base = cst_now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_cst = base - timedelta(days=days_ago)
    return start_cst.astimezone(timezone.utc)


def cst_day_range_utc(days_ago: int = 0) -> Tuple[datetime, datetime]:
    """
    北京时间某一天的 **[起, 止)** 半开区间（UTC aware）。

    返回 ``(当天 00:00 CST 的 UTC 时刻, 次日 00:00 CST 的 UTC 时刻)``。

    为什么推荐半开区间而不是 ``func.date(col) == ...``：
        - 语义准确：不依赖数据库会话时区；
        - **可命中时间列索引**：``func.date()`` 会使索引失效、退化为全表扫描。
    """
    start = cst_day_start_utc(days_ago)
    return start, start + timedelta(days=1)


def cst_day_range_utc_from_date(d: date) -> Tuple[datetime, datetime]:
    """
    北京时间某一日（**显式 ``date`` 对象**）的 **[起, 止)** 半开区间（UTC aware）。

    与 :func:`cst_day_range_utc` 的区别：本函数接受"指定的某一天"
    （如前端传来的 ``YYYY-MM-DD`` 参数、对账单日期），
    而不是相对今天偏移 N 天。

    典型场景：对账模块 —— 同一个 ``(起, 止)`` 既要作为**交易流水查询边界**，
    又要作为 ``reconcile_date`` 的**写入锚点**（当天 00:00 CST 的 UTC 时刻），
    两处必须来自同一函数，否则写入与查询会错位。
    """
    start_cst = datetime(d.year, d.month, d.day, tzinfo=CST)
    start = start_cst.astimezone(timezone.utc)
    return start, start + timedelta(days=1)


def cst_month_range_utc(year: int, month: int) -> Tuple[datetime, datetime]:
    """
    北京时间某个月的 **[起, 止)** 半开区间（UTC aware）。

    Args:
        year: 年份（北京时间口径）
        month: 月份（1-12，北京时间口径）
    """
    start_cst = datetime(year, month, 1, tzinfo=CST)
    if month == 12:
        end_cst = datetime(year + 1, 1, 1, tzinfo=CST)
    else:
        end_cst = datetime(year, month + 1, 1, tzinfo=CST)
    return start_cst.astimezone(timezone.utc), end_cst.astimezone(timezone.utc)


def cst_current_year_month() -> Tuple[int, int]:
    """当前北京时间的 ``(年, 月)`` —— 用于"默认统计月份"等场景"""
    now = cst_now()
    return now.year, now.month


def cst_date_str(days_ago: int = 0) -> str:
    """
    北京时间某天的 ``YYYY-MM-DD`` 字符串。

    仅用于**展示类**场景（如补零的图表日期标签）；
    涉及数据库查询请改用 :func:`cst_day_range_utc`。

    Args:
        days_ago: 0 = 今天，1 = 昨天，依此类推
    """
    base = cst_now().replace(hour=0, minute=0, second=0, microsecond=0)
    return (base - timedelta(days=days_ago)).strftime("%Y-%m-%d")


# ==================== SQL 表达式辅助（分组 / 标签） ====================

def cst_date_expr(column):
    """
    按**北京时间**取日期的 SQL 表达式（用于 ``group_by`` / 图表 label）。

    为什么需要：
        数据库按 UTC 存储；直接 ``func.date(created_at)`` 会按**会话时区**（本项目为 UTC）
        取日期，使"按天分组"的边界与中国用户的自然日错位 8 小时。
        改用 ``timezone('Asia/Shanghai', col)`` 先转业务时区再取日期即可。

    ⚠️ 用法限制（重要）：
        每次**调用**本函数都会生成新的绑定参数（``'Asia/Shanghai'`` 是绑定字面量）。
        同一条查询的 ``select`` / ``group_by`` / ``order_by`` 必须**复用同一表达式对象**：

            date_col = cst_date_expr(Bill.created_at).label("date")
            select(date_col, ...).group_by(date_col).order_by(date_col)   # ✅

            select(cst_date_expr(col), ...).group_by(cst_date_expr(col))  # ❌ GroupingError

        否则 PostgreSQL 会判定 SELECT 与 GROUP BY 的表达式不一致，抛出
        ``GroupingError: 字段 ... 必须出现在 GROUP BY 子句中``。
    """
    from sqlalchemy import func

    return func.date(func.timezone("Asia/Shanghai", column))


def cst_hour_expr(column):
    """按**北京时间**取小时起点的 SQL 表达式（用于按小时分组）"""
    from sqlalchemy import func

    return func.date_trunc("hour", func.timezone("Asia/Shanghai", column))
