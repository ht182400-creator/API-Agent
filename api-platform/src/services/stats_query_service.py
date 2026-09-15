"""
统计查询服务（P1-6 阶段 2）—— 预聚合优先 + 实时兜底

目标：
    在不改变任何统计口径的前提下，让 analytics 的大窗口聚合尽量走 ``repo_stats``
    （大表 ``api_call_logs`` 只承担"水位之后"的尾部查询与去重类查询）。

正确性三条铁律（零回归的关键）：
    1. **只用可加量**：``total_calls`` / ``success_calls`` / ``total_cost`` 是可加量，
       因此「预聚合段求和 + 实时段求和」与「直接对 api_call_logs 求和」**逐值相同**。
    2. **独立用户数不可加**：``repo_stats.unique_users`` 是「每仓库每小时」的去重计数，
       跨小时/跨仓库相加会重复计数（去重不可加）→ 本服务**一律实时查询**，
       绝不使用预聚合值。宁可慢，不可错。
    3. **水位诚实**：只有 ``[日志起点, aggregated_until)`` 这一段预聚合值可信，
       其后的尾部必须回落实时查询；没有水位（从未聚合过）则整段走实时。

窗口切分（:meth:`StatsQueryService.split_window`）::

    [start, end)  →  预聚合段 [start, agg_end)  +  实时段 [agg_end, end)
    agg_end = min(watermark, end)

    切分点固定在**整点水位**上，因此即使查询窗口是非整点（如 ``now - 7days``），
    两段拼接仍严格等价：落入预聚合段的小时都是"已完整聚合"的小时。

时区口径：
    分组统一走 ``src/utils/time_range.py`` 的 ``cst_date_expr`` / ``cst_hour_expr``
    （北京时间业务口径），与改造前的 analytics 输出标签完全一致。
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import Numeric, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logging_config import get_logger
from src.models.billing import APICallLog
from src.models.repository import RepoStats
from src.services.stats_aggregation_service import StatsAggregationService
from src.utils.time_range import cst_date_expr, cst_hour_expr

logger = get_logger("stats_query")

# 支持的分组粒度
PERIOD_DAY = "day"
PERIOD_HOUR = "hour"
_SUPPORTED_PERIODS = (PERIOD_DAY, PERIOD_HOUR)


def _empty_metrics() -> Dict[str, Any]:
    """空统计结果（无数据 / 无可访问仓库）"""
    return {"total_calls": 0, "success_calls": 0, "total_cost": Decimal("0")}


def _success_case(status_column):
    """
    成功调用判定（**2xx**）—— 与 ``StatsAggregationService`` 保持同一口径。

    口径统一（P1-6 阶段 2）：阶段 1 曾用 ``< 400``，会让 3xx 被计为成功，
    与 analytics 既有的 2xx 口径不一致；统一后预聚合值与实时值逐值相同。
    """
    return case(
        (
            status_column.isnot(None)
            & (status_column >= 200)
            & (status_column < 300),
            1,
        ),
        else_=0,
    )


def _merge_group_rows(merged: Dict[Any, Dict[str, Any]], rows: Iterable[Dict[str, Any]]) -> None:
    """把分组结果并入累加表（预聚合段 + 实时段合并的公共逻辑）"""
    for row in rows:
        item = merged.setdefault(row["key"], {"calls": 0, "cost": Decimal("0")})
        item["calls"] += int(row["calls"] or 0)
        item["cost"] += Decimal(str(row["cost"] or 0))


def _merge_repo_rows(merged: Dict[Any, Dict[str, Any]], rows: Iterable[Dict[str, Any]]) -> None:
    """把「按仓库」分组结果并入累加表（含成功数）"""
    for row in rows:
        item = merged.setdefault(
            row["key"],
            {"total_calls": 0, "success_calls": 0, "total_cost": Decimal("0")},
        )
        item["total_calls"] += int(row["calls"] or 0)
        item["success_calls"] += int(row["success"] or 0)
        item["total_cost"] += Decimal(str(row["cost"] or 0))


class StatsQueryService:
    """
    analytics 读取统一入口：预聚合优先 + 实时兜底。

    典型用法::

        svc = StatsQueryService(db)
        metrics = await svc.sum_metrics(start, end, repo_ids=user_repo_ids)
        active = await svc.count_distinct_users(start, end, repo_ids=user_repo_ids)
        trend = await svc.group_by_period(start, end, period="day", repo_ids=user_repo_ids)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        # 复用聚合服务读取水位（只读，不复用其写路径）
        self._aggregation = StatsAggregationService(db)

    # ==================== 窗口切分 ====================

    async def get_watermark(self) -> Optional[datetime]:
        """
        当前聚合水位（已**连续**聚合到的排他上界，UTC 整点）。

        Returns:
            水位值；从未聚合过时返回 None（调用方视为"没有可用的预聚合数据"）
        """
        return await self._aggregation.get_watermark()

    async def split_window(
        self, start: datetime, end: datetime
    ) -> Tuple[Optional[datetime], datetime]:
        """
        把查询窗口 [start, end) 拆成「预聚合段 + 实时段」。

        Returns:
            ``(agg_end, live_start)``
            - ``agg_end``：预聚合段的排他上界；None 表示本窗口完全不使用预聚合
            - ``live_start``：实时段起点（= agg_end，或 start）
        """
        watermark = await self.get_watermark()
        if watermark is None or watermark <= start:
            # 没有水位，或水位没盖住窗口起点 → 整段实时（保证正确性）
            logger.debug(
                "[StatsQuery] 回落实时查询: watermark=%s window=[%s, %s)",
                watermark.isoformat() if watermark else "None", start.isoformat(), end.isoformat(),
            )
            return None, start
        agg_end = min(watermark, end)
        return agg_end, agg_end

    # ==================== 标量求和 ====================

    async def sum_metrics(
        self,
        start: datetime,
        end: datetime,
        repo_ids: Optional[Sequence[Any]] = None,
    ) -> Dict[str, Any]:
        """
        统计 [start, end) 内的调用数 / 成功数 / 成本（**与实时查询逐值一致**）。

        Args:
            start/end: aware datetime（UTC 或 CST 均可，asyncpg 按 UTC 比较）
            repo_ids: None = 不过滤（管理员全局）；空列表 = 无可访问仓库（直接返回 0）

        Returns:
            ``{"total_calls": int, "success_calls": int, "total_cost": Decimal}``
        """
        if end <= start:
            return _empty_metrics()
        if repo_ids is not None and len(repo_ids) == 0:
            return _empty_metrics()

        agg_end, live_start = await self.split_window(start, end)

        total_calls = 0
        success_calls = 0
        total_cost = Decimal("0")

        if agg_end is not None and agg_end > start:
            agg = await self._sum_preaggregated(start, agg_end, repo_ids)
            total_calls += agg["total_calls"]
            success_calls += agg["success_calls"]
            total_cost += agg["total_cost"]

        if live_start < end:
            live = await self._sum_live(live_start, end, repo_ids)
            total_calls += live["total_calls"]
            success_calls += live["success_calls"]
            total_cost += live["total_cost"]

        return {
            "total_calls": total_calls,
            "success_calls": success_calls,
            "total_cost": total_cost,
        }

    async def count_distinct_users(
        self,
        start: datetime,
        end: datetime,
        repo_ids: Optional[Sequence[Any]] = None,
    ) -> int:
        """
        窗口内独立用户数 —— **始终实时查询**（不使用预聚合）。

        原因：``repo_stats.unique_users`` 是每仓库每小时的去重数，去重结果**不可加**，
        跨小时求和会把同一用户重复计数。
        """
        if end <= start:
            return 0
        if repo_ids is not None and len(repo_ids) == 0:
            return 0

        stmt = select(func.count(func.distinct(APICallLog.user_id))).where(
            APICallLog.created_at >= start,
            APICallLog.created_at < end,
        )
        if repo_ids is not None:
            stmt = stmt.where(APICallLog.repo_id.in_(repo_ids))

        value = (await self.db.execute(stmt)).scalar()
        return int(value or 0)

    # ==================== 分段求和（内部） ====================

    async def _sum_preaggregated(
        self, start: datetime, end: datetime, repo_ids: Optional[Sequence[Any]]
    ) -> Dict[str, Any]:
        """预聚合段求和（repo_stats 按整点小时存行，可加量直接相加）"""
        stmt = select(
            func.coalesce(func.sum(RepoStats.total_calls), 0),
            func.coalesce(func.sum(RepoStats.success_calls), 0),
            func.coalesce(func.sum(cast(RepoStats.total_cost, Numeric)), 0),
        ).where(
            RepoStats.stat_hour >= start,
            RepoStats.stat_hour < end,
        )
        if repo_ids is not None:
            stmt = stmt.where(RepoStats.repo_id.in_(repo_ids))

        row = (await self.db.execute(stmt)).one()
        return {
            "total_calls": int(row[0] or 0),
            "success_calls": int(row[1] or 0),
            "total_cost": Decimal(str(row[2] or 0)),
        }

    async def _sum_live(
        self, start: datetime, end: datetime, repo_ids: Optional[Sequence[Any]]
    ) -> Dict[str, Any]:
        """实时段求和（直接聚合 api_call_logs）"""
        stmt = select(
            func.count(APICallLog.id),
            func.coalesce(func.sum(_success_case(APICallLog.status_code)), 0),
            func.coalesce(func.sum(cast(APICallLog.cost, Numeric)), 0),
        ).where(
            APICallLog.created_at >= start,
            APICallLog.created_at < end,
        )
        if repo_ids is not None:
            stmt = stmt.where(APICallLog.repo_id.in_(repo_ids))

        row = (await self.db.execute(stmt)).one()
        return {
            "total_calls": int(row[0] or 0),
            "success_calls": int(row[1] or 0),
            "total_cost": Decimal(str(row[2] or 0)),
        }

    # ==================== 分组（趋势 / 排行） ====================

    async def group_by_period(
        self,
        start: datetime,
        end: datetime,
        period: str = PERIOD_DAY,
        repo_ids: Optional[Sequence[Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        按北京时间「天 / 小时」分组统计调用量与成本（预聚合段与实时段自动合并）。

        Args:
            period: ``"day"``（北京时间自然日）或 ``"hour"``（北京时间整点）

        Returns:
            按时间升序的 ``[{"key": date|datetime, "calls": int, "cost": Decimal}]``；
            ``key`` 为北京时间口径的分组键（day → ``date``；hour → naive ``datetime``），
            调用方据此生成图表 label（与改造前完全一致）。
        """
        if period not in _SUPPORTED_PERIODS:
            raise ValueError(f"不支持的分组粒度: {period}")
        if end <= start:
            return []
        if repo_ids is not None and len(repo_ids) == 0:
            return []

        merged: Dict[Any, Dict[str, Any]] = {}

        agg_end, live_start = await self.split_window(start, end)
        if agg_end is not None and agg_end > start:
            _merge_group_rows(merged, await self._group_preaggregated(start, agg_end, period, repo_ids))
        if live_start < end:
            _merge_group_rows(merged, await self._group_live(live_start, end, period, repo_ids))

        return [{"key": key, **value} for key, value in sorted(merged.items(), key=lambda kv: kv[0])]

    async def _group_preaggregated(
        self,
        start: datetime,
        end: datetime,
        period: str,
        repo_ids: Optional[Sequence[Any]],
    ) -> List[Dict[str, Any]]:
        """预聚合段分组（repo_stats 按整点小时 → 转北京时间再按天/小时分组）"""
        # ⚠️ 表达式只生成一次并复用（cst_*_expr 每次调用都会生成新的绑定参数 → GroupingError）
        if period == PERIOD_DAY:
            period_col = cst_date_expr(RepoStats.stat_hour).label("period_key")
        else:
            period_col = cst_hour_expr(RepoStats.stat_hour).label("period_key")

        stmt = select(
            period_col,
            func.coalesce(func.sum(RepoStats.total_calls), 0).label("calls"),
            func.coalesce(func.sum(cast(RepoStats.total_cost, Numeric)), 0).label("cost"),
        ).where(
            RepoStats.stat_hour >= start,
            RepoStats.stat_hour < end,
        )
        if repo_ids is not None:
            stmt = stmt.where(RepoStats.repo_id.in_(repo_ids))
        stmt = stmt.group_by(period_col).order_by(period_col)

        rows = (await self.db.execute(stmt)).all()
        return [{"key": row.period_key, "calls": row.calls, "cost": row.cost} for row in rows]

    async def _group_live(
        self,
        start: datetime,
        end: datetime,
        period: str,
        repo_ids: Optional[Sequence[Any]],
    ) -> List[Dict[str, Any]]:
        """实时段分组（api_call_logs 直接聚合）"""
        if period == PERIOD_DAY:
            period_col = cst_date_expr(APICallLog.created_at).label("period_key")
        else:
            period_col = cst_hour_expr(APICallLog.created_at).label("period_key")

        stmt = select(
            period_col,
            func.count(APICallLog.id).label("calls"),
            func.coalesce(func.sum(cast(APICallLog.cost, Numeric)), 0).label("cost"),
        ).where(
            APICallLog.created_at >= start,
            APICallLog.created_at < end,
        )
        if repo_ids is not None:
            stmt = stmt.where(APICallLog.repo_id.in_(repo_ids))
        stmt = stmt.group_by(period_col).order_by(period_col)

        rows = (await self.db.execute(stmt)).all()
        return [{"key": row.period_key, "calls": row.calls, "cost": row.cost} for row in rows]

    # ==================== 按仓库分组（明细 / 排行） ====================

    async def group_by_repo(
        self,
        start: datetime,
        end: datetime,
        repo_ids: Optional[Sequence[Any]] = None,
    ) -> Dict[Any, Dict[str, Any]]:
        """
        按仓库分组统计调用数 / 成功数 / 成本（预聚合段 + 实时段自动合并）。

        用途：``/analytics/repo-details`` 与 ``/analytics/repo-ranking`` ——
        替代原先"每个仓库各查 3 次"的 N×3 查询（一次分组即可拿到全部仓库）。

        Returns:
            ``{repo_id: {"total_calls": int, "success_calls": int, "total_cost": Decimal}}``
            仅包含**有调用记录**的仓库；无调用的仓库不在字典中，调用方按 0 处理。
        """
        if end <= start:
            return {}
        if repo_ids is not None and len(repo_ids) == 0:
            return {}

        merged: Dict[Any, Dict[str, Any]] = {}

        agg_end, live_start = await self.split_window(start, end)
        if agg_end is not None and agg_end > start:
            _merge_repo_rows(merged, await self._group_repo_preaggregated(start, agg_end, repo_ids))
        if live_start < end:
            _merge_repo_rows(merged, await self._group_repo_live(live_start, end, repo_ids))

        return merged

    async def _group_repo_preaggregated(
        self, start: datetime, end: datetime, repo_ids: Optional[Sequence[Any]]
    ) -> List[Dict[str, Any]]:
        """预聚合段：按 repo_id 分组"""
        stmt = select(
            RepoStats.repo_id,
            func.coalesce(func.sum(RepoStats.total_calls), 0).label("calls"),
            func.coalesce(func.sum(RepoStats.success_calls), 0).label("success"),
            func.coalesce(func.sum(cast(RepoStats.total_cost, Numeric)), 0).label("cost"),
        ).where(
            RepoStats.stat_hour >= start,
            RepoStats.stat_hour < end,
        )
        if repo_ids is not None:
            stmt = stmt.where(RepoStats.repo_id.in_(repo_ids))
        stmt = stmt.group_by(RepoStats.repo_id)

        rows = (await self.db.execute(stmt)).all()
        return [{"key": row[0], "calls": row[1], "success": row[2], "cost": row[3]} for row in rows]

    async def _group_repo_live(
        self, start: datetime, end: datetime, repo_ids: Optional[Sequence[Any]]
    ) -> List[Dict[str, Any]]:
        """实时段：按 repo_id 分组"""
        stmt = select(
            APICallLog.repo_id,
            func.count(APICallLog.id).label("calls"),
            func.coalesce(func.sum(_success_case(APICallLog.status_code)), 0).label("success"),
            func.coalesce(func.sum(cast(APICallLog.cost, Numeric)), 0).label("cost"),
        ).where(
            APICallLog.created_at >= start,
            APICallLog.created_at < end,
        )
        if repo_ids is not None:
            stmt = stmt.where(APICallLog.repo_id.in_(repo_ids))
        stmt = stmt.group_by(APICallLog.repo_id)

        rows = (await self.db.execute(stmt)).all()
        return [{"key": row[0], "calls": row[1], "success": row[2], "cost": row[3]} for row in rows]
