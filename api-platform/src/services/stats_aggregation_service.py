"""
统计预聚合服务（P1-6）

问题：
    analytics/dashboard 类接口直接对 ``api_call_logs`` 实时 COUNT/SUM/GROUP BY，
    数据量增长后会拖垮主库。

方案（backlog §3.2）：
    ① 按小时聚合 ``api_call_logs`` → ``repo_stats``（阶段 1 ✅）
    ② 读切换：analytics 优先读预聚合（阶段 2 ✅ —— 依赖本模块维护的**聚合水位**）
    ③ 结果缓存：Redis TTL 60s（阶段 3，调用方见 ``src/core/cache.py``）

幂等性（验收标准之一）：
    ``repo_stats`` 有唯一约束 ``uq_repo_stats_repo_hour``（repo_id + stat_hour），
    本服务采用「先查后 upsert」—— 重复执行**覆盖**同一行而非新增，
    任意时刻重复跑聚合结果一致。

连续性（阶段 2 新增，正确性关键）：
    ``repo_stats`` 只对「该小时确实有调用」的 (repo, hour) 写入行，无调用的小时**没有行**，
    因此表内 ``max(stat_hour)`` 无法证明中间没有空洞（停机数日后重新聚合，
    max 会直接跳到最新，中间的洞不可见）。本服务把"已连续聚合到哪"显式记录在
    ``stats_aggregation_state.aggregated_until``（单行水位）；读侧
    （``src/services/stats_query_service.py``）据此把窗口拆成
    「预聚合段 + 实时兜底段」，保证与实时查询**逐值一致**。

时间口径：
    ``stat_hour`` 按 **UTC 整点** 存储（timestamptz）。北京时间自然日/小时边界换算成 UTC
    后仍是整点，因此按整点聚合的行可以直接求和还原任意"整点对齐"窗口。
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from sqlalchemy import case, cast, func, select, Numeric
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logging_config import get_logger
from src.models.billing import APICallLog
from src.models.repository import RepoStats, StatsAggregationState

logger = get_logger("stats_aggregation")

# 水位单行主键（固定值，避免出现多行状态互相矛盾）
_WATERMARK_SINGLETON_ID = 1

# 单次聚合的最大小时数（30 天）：防止首次历史回填把调度循环与数据库拖住，
# 未追上的部分由调度循环以 CATCHUP_INTERVAL_SECONDS 加快轮询继续推进。
MAX_HOURS_PER_RUN = 24 * 30

# 追赶模式轮询间隔（秒）：水位尚未追上"当前整点"时使用更短的间隔
CATCHUP_INTERVAL_SECONDS = 60


def _floor_to_hour(value: datetime) -> datetime:
    """
    把 datetime 向下取整到 UTC 整点（统一为 aware UTC）。

    容错：从数据库读出的 timestamptz 正常是 aware；若为 naive（历史数据/非常规驱动），
    按 UTC 补齐时区，避免后续比较抛 ``TypeError``。
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


class StatsAggregationService:
    """api_call_logs → repo_stats 小时级聚合（含连续性水位维护）"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== 水位（连续性）====================

    async def get_watermark(self) -> Optional[datetime]:
        """
        读取当前聚合水位（已**连续**聚合到的排他上界，UTC 整点）。

        Returns:
            水位值；从未初始化过时返回 None（调用方应视为"没有任何预聚合数据"）
        """
        result = await self.db.execute(
            select(StatsAggregationState.aggregated_until).where(
                StatsAggregationState.id == _WATERMARK_SINGLETON_ID
            )
        )
        value = result.scalar_one_or_none()
        if value is None:
            logger.debug("[StatsAggregation] 水位尚未初始化")
            return None
        return _floor_to_hour(value)

    async def _init_watermark(self, current_hour: datetime) -> datetime:
        """
        首次初始化水位：取「最早日志所在整点」，没有日志则取当前整点。

        ⚠️ 绝不能把水位直接设为"当前整点"——水位语义是"确实聚合过"，
        谎报水位会让读侧把未聚合的历史窗口当成有效数据，**静默漏算**。
        """
        min_created = (await self.db.execute(
            select(func.min(APICallLog.created_at))
        )).scalar()

        start = _floor_to_hour(min_created) if min_created is not None else current_hour
        state = StatsAggregationState(
            id=_WATERMARK_SINGLETON_ID,
            aggregated_until=start,
        )
        self.db.add(state)
        await self.db.commit()

        logger.info(
            "[StatsAggregation] 水位初始化: aggregated_until=%s（最早日志=%s）",
            start.isoformat(), min_created.isoformat() if min_created else "无",
        )
        return start

    async def _get_or_init_watermark(self, current_hour: datetime) -> datetime:
        """读取水位；不存在则按最早日志初始化"""
        watermark = await self.get_watermark()
        if watermark is None:
            watermark = await self._init_watermark(current_hour)
        return watermark

    async def _advance_watermark(self, value: datetime) -> None:
        """推进水位（只允许向前；回退会被忽略并告警）"""
        value = _floor_to_hour(value)
        result = await self.db.execute(
            select(StatsAggregationState).where(
                StatsAggregationState.id == _WATERMARK_SINGLETON_ID
            )
        )
        state = result.scalar_one_or_none()
        if state is None:
            state = StatsAggregationState(id=_WATERMARK_SINGLETON_ID, aggregated_until=value)
            self.db.add(state)
            await self.db.commit()
            return

        current = _floor_to_hour(state.aggregated_until)
        if value <= current:
            logger.warning(
                "[StatsAggregation] 水位未推进（忽略回退）: 当前=%s 目标=%s",
                current.isoformat(), value.isoformat(),
            )
            return

        state.aggregated_until = value
        state.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

    # ==================== 聚合 ====================

    async def aggregate_range(self, start: datetime, end: datetime) -> Dict[str, int]:
        """
        聚合 **[start, end)** 半开区间内的调用日志（UTC aware）。

        Returns:
            {"hours": 参与聚合的小时数, "upserted": 写入/更新的 repo_stats 行数}
        """
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("aggregate_range 需要 aware datetime（UTC）")
        if start >= end:
            return {"hours": 0, "upserted": 0}

        # 按小时聚合（SQL 层完成，应用层只做 upsert）
        # ⚠️ date_trunc("hour", ...) 与 cst_date_expr 同坑：字面量 "hour" 是绑定参数，
        #    select/group_by 必须**复用同一表达式对象**，否则 PostgreSQL GroupingError。
        hour_expr = func.date_trunc("hour", APICallLog.created_at)
        stmt = select(
            APICallLog.repo_id,
            hour_expr.label("stat_hour"),
            func.count(APICallLog.id).label("total_calls"),
            # 【口径统一（P1-6 阶段 2）】成功 = 2xx，与 analytics/dashboard 既有口径一致。
            #   阶段 1 曾用 status_code < 400，会把 3xx 计为成功 → 与实时查询结果不一致；
            #   统一为 2xx 后，预聚合段求和与实时查询**逐值相同**。NULL status_code 记为失败。
            func.sum(
                case(
                    (
                        APICallLog.status_code.isnot(None)
                        & (APICallLog.status_code >= 200)
                        & (APICallLog.status_code < 300),
                        1,
                    ),
                    else_=0,
                )
            ).label("success_calls"),
            func.coalesce(func.sum(APICallLog.tokens_used), 0).label("total_tokens"),
            func.sum(cast(APICallLog.cost, Numeric)).label("total_cost"),
            func.avg(
                cast(APICallLog.response_time, Numeric)
            ).label("avg_latency_ms"),
            func.count(func.distinct(APICallLog.user_id)).label("unique_users"),
        ).where(
            APICallLog.created_at >= start,
            APICallLog.created_at < end,
        ).group_by(
            APICallLog.repo_id,
            hour_expr,
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        upserted = 0
        for row in rows:
            stat_hour = _floor_to_hour(row.stat_hour)
            total_calls = int(row.total_calls or 0)
            success_calls = int(row.success_calls or 0)

            # upsert：按唯一维度查已有行（幂等 —— 重复执行覆盖）
            existing = await self.db.execute(
                select(RepoStats).where(
                    RepoStats.repo_id == row.repo_id,
                    RepoStats.stat_hour == stat_hour,
                )
            )
            stat = existing.scalar_one_or_none()

            avg_latency = str(round(float(row.avg_latency_ms), 2)) if row.avg_latency_ms is not None else None
            total_cost = str(row.total_cost) if row.total_cost is not None else "0"

            if stat is None:
                stat = RepoStats(
                    repo_id=row.repo_id,
                    stat_hour=stat_hour,
                    total_calls=total_calls,
                    success_calls=success_calls,
                    failed_calls=total_calls - success_calls,
                    avg_latency_ms=avg_latency,
                    total_tokens=int(row.total_tokens or 0),
                    total_cost=total_cost,
                    unique_users=int(row.unique_users or 0),
                )
                self.db.add(stat)
            else:
                stat.total_calls = total_calls
                stat.success_calls = success_calls
                stat.failed_calls = total_calls - success_calls
                stat.avg_latency_ms = avg_latency
                stat.total_tokens = int(row.total_tokens or 0)
                stat.total_cost = total_cost
                stat.unique_users = int(row.unique_users or 0)
            upserted += 1

        await self.db.commit()

        hours = int((end - start).total_seconds() // 3600)
        logger.info(
            "[StatsAggregation] 聚合完成: 窗口=[%s, %s) 小时数=%s upserted=%s",
            start.isoformat(), end.isoformat(), hours, upserted,
        )
        return {"hours": hours, "upserted": upserted}

    async def aggregate_recent_hours(self, hours: int = 2) -> Dict[str, int]:
        """
        聚合「当前整点之前的最近 N 个小时」（**不推进水位**，仅补数据）。

        默认 N=2：补上个小时 + 上上个小时，防止调度间隙漏数据。
        例：现在 10:35，hours=2 → 聚合 [08:00, 10:00)。
        """
        now = datetime.now(timezone.utc)
        current_hour = _floor_to_hour(now)
        end = current_hour
        start = end - timedelta(hours=hours)
        return await self.aggregate_range(start, end)

    async def aggregate_until_now(self, max_hours_per_run: int = MAX_HOURS_PER_RUN) -> Dict[str, int]:
        """
        **从水位连续聚合到当前整点**（阶段 2 主入口，保证不留空洞）。

        流程：
            1. 读水位（不存在则按最早日志初始化）；
            2. 若水位 >= 当前整点 → 无事可做；
            3. 否则聚合 [水位, min(当前整点, 水位 + max_hours_per_run))；
            4. 成功推进水位（同一事务提交）。

        Returns:
            {"hours": 本轮聚合小时数, "upserted": 写入行数, "remaining_hours": 尚未追上的小时数}
        """
        if max_hours_per_run <= 0:
            raise ValueError("max_hours_per_run 必须为正数")

        current_hour = _floor_to_hour(datetime.now(timezone.utc))
        watermark = await self._get_or_init_watermark(current_hour)

        if watermark >= current_hour:
            logger.debug("[StatsAggregation] 水位已追上当前整点: %s", watermark.isoformat())
            return {"hours": 0, "upserted": 0, "remaining_hours": 0}

        end = min(current_hour, watermark + timedelta(hours=max_hours_per_run))
        result = await self.aggregate_range(watermark, end)
        await self._advance_watermark(end)

        remaining = int((current_hour - end).total_seconds() // 3600)
        if remaining > 0:
            logger.info(
                "[StatsAggregation] 水位推进至 %s，仍有 %s 小时待回填（下轮继续）",
                end.isoformat(), remaining,
            )

        return {
            "hours": result["hours"],
            "upserted": result["upserted"],
            "remaining_hours": remaining,
        }
