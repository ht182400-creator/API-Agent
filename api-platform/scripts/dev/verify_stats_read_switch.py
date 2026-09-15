"""
【一次性验证脚本】P1-6 阶段 2「读切换」在真实开发库上的数值一致性。

背景：
    analytics 的统计读取已改为「预聚合优先 + 实时兜底」（`src/services/stats_query_service.py`）。
    正确性的唯一可信证据是：**同一窗口下，切换后的读取结果与直接实时查询逐值一致**。

做法：
    1. 记录当前水位，对 overview 的四个窗口（今日 / 本周 / 本月 / 全部）
       对比「StatsQueryService」与「直接实时 SQL」；
       若无水位，应观察到"预聚合段上界 = -"（即全回落实时）；
    2. 执行一次 `aggregate_until_now()` 建立/推进水位（会写入 repo_stats，属正常业务行为）；
    3. 再次对比 —— 此时窗口应走预聚合段（或预聚合 + 实时尾部），数值仍必须一致。

用法（在 api-platform 目录下执行）：
    python scripts/dev/verify_stats_read_switch.py                     # 只读校验（库里有数据才有说服力）
    python scripts/dev/verify_stats_read_switch.py --seed              # 先造临时日志再校验，结束后自动清理
    python scripts/dev/verify_stats_read_switch.py --reset-watermark   # 清空聚合水位（强制全量重算）
退出码：0 = 全部一致；1 = 存在不一致（需排查）；2 = 脚本异常
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy import Numeric, and_, cast, delete, func, select

# 允许以 `python scripts/dev/xxx.py` 方式直接运行（否则 sys.path[0] 是脚本目录，导不到 src）
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.config.database import AsyncSessionLocal
from src.models.repository import Repository, RepoStats, StatsAggregationState
from src.models.billing import APICallLog
from src.services.stats_aggregation_service import StatsAggregationService
from src.services.stats_query_service import StatsQueryService
from src.utils.time_range import cst_day_range_utc, cst_now

# 统一日志格式（毫秒级，便于与业务日志对齐排查）
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s.%(msecs)03d] %(levelname)-5s %(name)s:%(lineno)d  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger("verify_stats")

# "全部时间"锚点（与 analytics.py 的 _ALL_TIME_START_UTC 保持一致）
ALL_TIME_START_UTC = datetime(1970, 1, 1, tzinfo=timezone.utc)


async def _live_baseline(session, start: datetime, end: datetime) -> Tuple[int, int, Decimal]:
    """直接实时查询基准（FILTER 写法，与实现解耦）"""
    stmt = select(
        func.count(APICallLog.id),
        func.count(APICallLog.id).filter(
            and_(APICallLog.status_code >= 200, APICallLog.status_code < 300)
        ),
        func.coalesce(func.sum(cast(APICallLog.cost, Numeric)), 0),
    ).where(APICallLog.created_at >= start, APICallLog.created_at < end)

    row = (await session.execute(stmt)).one()
    return int(row[0] or 0), int(row[1] or 0), Decimal(str(row[2] or 0))


async def _seed_temp_logs(session) -> Tuple[Optional[object], Optional[datetime], Optional[datetime], list]:
    """
    造一批临时调用日志（跨 4 个整点小时，含 2xx / 3xx / 5xx 与不同金额）。

    关键：造数前把**水位清空**。否则若水位已覆盖 seed 窗口、但对应的 repo_stats 行不存在
    （例如手工清理过），读侧会误判"已聚合"→ 漏算，校验就失去意义。

    Returns:
        (repo_id, window_start, window_end, log_ids)；无可用仓库时返回 (None, None, None, [])
    """
    repo = (await session.execute(select(Repository).limit(1))).scalars().first()
    if repo is None:
        logger.warning("[seed] 库中没有任何仓库，跳过造数（请先执行 scripts/init_db_with_data.py）")
        return None, None, None, []

    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=4)
    end = start + timedelta(hours=4)

    # 清理该窗口可能残留的旧聚合行，并清空水位（从"未聚合"状态开始校验）
    await session.execute(delete(RepoStats).where(
        RepoStats.repo_id == repo.id,
        RepoStats.stat_hour >= start,
        RepoStats.stat_hour < end,
    ))
    await session.execute(delete(StatsAggregationState))
    await session.commit()

    logs = []
    for hour_offset in range(4):
        for minute_offset, (status, cost) in enumerate([(200, "0.10"), (302, "0.20"), (500, "0.30")]):
            logs.append(APICallLog(
                repo_id=repo.id,
                user_id=repo.owner_id,
                status_code=status,
                cost=cost,
                response_time="120",
                tokens_used=10,
                created_at=start + timedelta(hours=hour_offset, minutes=minute_offset + 1),
            ))

    session.add_all(logs)
    await session.flush()
    log_ids = [log.id for log in logs]
    await session.commit()

    logger.info(
        "[seed] 已插入 %s 条临时日志：仓库=%s 窗口=[%s, %s)（2 小时供预聚合段 + 2 小时留作实时尾部）",
        len(logs), repo.id, start.isoformat(), end.isoformat(),
    )
    return repo.id, start, end, log_ids


async def _cleanup_temp(session, repo_id, start, end, log_ids, before_watermark) -> None:
    """清理 seed 数据并恢复水位（保证脚本对数据库"零残留"）"""
    if repo_id is not None and log_ids:
        await session.execute(delete(APICallLog).where(APICallLog.id.in_(log_ids)))
        await session.execute(delete(RepoStats).where(
            RepoStats.repo_id == repo_id,
            RepoStats.stat_hour >= start,
            RepoStats.stat_hour < end,
        ))
        await session.commit()
        logger.info("[cleanup] 已删除 %s 条临时日志及其聚合行", len(log_ids))

    # 恢复水位（脚本运行期间可能建立/推进过水位）
    if before_watermark is None:
        await session.execute(delete(StatsAggregationState))
    else:
        state = (await session.execute(
            select(StatsAggregationState).where(StatsAggregationState.id == 1)
        )).scalar_one_or_none()
        if state is not None:
            state.aggregated_until = before_watermark
    await session.commit()
    logger.info(
        "[cleanup] 水位已恢复为 %s",
        before_watermark.isoformat() if before_watermark else "None（未聚合）",
    )


def _build_windows() -> dict:
    """overview 使用的四个统计窗口（与接口实现保持一致）"""
    now = cst_now()
    today_start, today_end = cst_day_range_utc()
    return {
        "today": (today_start, today_end),
        "week": (now - timedelta(days=7), now),
        "month": (now - timedelta(days=30), now),
        "all": (ALL_TIME_START_UTC, now),
    }


async def main() -> int:
    seed = "--seed" in sys.argv
    windows = _build_windows()
    mismatches = 0

    async with AsyncSessionLocal() as session:
        if "--reset-watermark" in sys.argv:
            # 清空水位：下次聚合会从"最早日志整点"重新开始（口径变更 / 需要强制重算时使用）。
            # 注意：清空后读侧会自动全部回落实时查询，因此**数值始终正确**，只是暂时失去预聚合加速。
            await session.execute(delete(StatsAggregationState))
            await session.commit()
            logger.info("[reset] 已清空聚合水位（下次聚合将从最早日志重新开始）")
            return 0

        query = StatsQueryService(session)
        aggregation = StatsAggregationService(session)

        before_watermark = await query.get_watermark()
        logger.info(
            "当前聚合水位: %s（脚本结束时恢复）",
            before_watermark.isoformat() if before_watermark else "None（尚未聚合 → 读侧应全部回落实时）",
        )

        async def compare(stage: str) -> None:
            nonlocal mismatches
            for name, (start, end) in windows.items():
                actual = await query.sum_metrics(start, end)
                base_calls, base_success, base_cost = await _live_baseline(session, start, end)
                agg_end, live_start = await query.split_window(start, end)

                ok = (
                    actual["total_calls"] == base_calls
                    and actual["success_calls"] == base_success
                    and float(actual["total_cost"]) == float(base_cost)
                )
                if not ok:
                    mismatches += 1

                logger.info(
                    "[%s] %-5s 预聚合段上界=%-25s 实时段起点=%-25s | 服务=(%s, %s, %s) 基准=(%s, %s, %s) -> %s",
                    stage, name,
                    agg_end.isoformat() if agg_end else "-",
                    live_start.isoformat(),
                    actual["total_calls"], actual["success_calls"], float(actual["total_cost"]),
                    base_calls, base_success, float(base_cost),
                    "OK" if ok else "MISMATCH",
                )

        repo_id = start = end = None
        log_ids = []
        if seed:
            repo_id, start, end, log_ids = await _seed_temp_logs(session)

        try:
            await compare("切换前")

            logger.info("执行 aggregate_until_now() 建立/推进水位（写入 repo_stats）...")
            result = await aggregation.aggregate_until_now()
            logger.info("聚合结果: %s", result)

            await compare("切换后")
        finally:
            # 无论校验结果如何，都要清理临时数据并恢复水位（对库零残留）
            if seed:
                await _cleanup_temp(session, repo_id, start, end, log_ids, before_watermark)

    if mismatches:
        logger.error("一致性校验失败：%s 个窗口不匹配，请排查 StatsQueryService 的分段逻辑", mismatches)
        return 1

    logger.info("一致性校验通过：所有窗口的读取结果与实时基准逐值一致")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception as exc:  # noqa: BLE001 脚本级兜底：打印完整堆栈便于定位
        import traceback

        logger.error("校验脚本异常: %s\n%s", exc, traceback.format_exc())
        sys.exit(2)
