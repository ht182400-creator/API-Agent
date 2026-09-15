"""
统计查询服务测试（P1-6 阶段 2）—— 预聚合优先 + 实时兜底

核心验收标准：**零回归**
    无论查询走「全实时」「全预聚合」还是「预聚合段 + 实时尾部」，
    结果必须与"直接实时查询 api_call_logs"**逐值一致**。

覆盖：
1. 无水位 → 全部回落实时
2. 水位覆盖整个窗口 → 全走预聚合（数值仍与实时一致）
3. 混合窗口（预聚合段 + 实时尾部）
4. repo_ids 过滤 / 空列表边界
5. 独立用户数**不可加**（必须实时，跨小时不能求和）
6. 按天/按小时分组的预聚合 + 实时合并
7. 按仓库分组的预聚合 + 实时合并
8. 水位初始化（最早日志整点）/ 分轮追赶 / 不回退
9. 成功口径统一为 2xx（3xx 不算成功），预聚合与实时一致

用例编号：TC-STATQ-001 ~ TC-STATQ-012
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import and_, cast, func, select, Numeric

from src.models.billing import APICallLog
from src.models.repository import Repository, RepoStats, StatsAggregationState
from src.services.stats_aggregation_service import StatsAggregationService
from src.services.stats_query_service import (
    PERIOD_DAY,
    PERIOD_HOUR,
    StatsQueryService,
)

# 水位单行主键（与 StatsAggregationService._WATERMARK_SINGLETON_ID 一致）
_WATERMARK_ID = 1


def _hour_base() -> datetime:
    """对齐到 UTC 当前整点，再往前推 3 小时（远离"当前小时"边界）。

    ⚠️ 该锚点被两类用例共享，**不能**改成固定钟点：
    - 水位/追赶类（TC-STATQ-008/009）隐式依赖「h 距当前整点约 3 小时」
      （`aggregate_until_now()` 要从 h 追平到 now，009 还断言"h 距 now 3 小时"）；
    - 分组类只要求"相对关系"，不关心绝对钟点。
    """
    now = datetime.now(timezone.utc)
    return (now - timedelta(hours=3)).replace(minute=0, second=0, microsecond=0)


def _day_base() -> datetime:
    """返回「北京时间当天 12:00」对应的 UTC 时刻 —— 专供**跨自然日分组**用例。

    ⚠️ group_by_period 按**北京时间自然日**分组（见其 docstring，9-15 时区口径收敛的
    有意设计）。若用 `_hour_base()`（UTC 整点）构造"跨 2 天"数据，当 UTC 处于
    16:00~20:00（= 北京 0:00~4:00）时，`h-1` 与 `h+24` 会横跨 **3 个**北京自然日，
    用例在每天这 4 小时窗口内**必挂** —— 回归实测：UTC 19:21 全量运行时
    TC-STATQ-006 `assert len(rows) == 2` 得到 3（9-15/9-16/9-17）。

    锚在北京时间 12:00：`h-1`/`h` 同日、`h+24` 恰为次日，**任意时刻运行都不跨界**。
    """
    bj_now = datetime.now(timezone.utc) + timedelta(hours=8)
    bj_noon = bj_now.replace(hour=12, minute=0, second=0, microsecond=0)
    return bj_noon - timedelta(hours=8)


async def _make_repo(db, test_user, name: str) -> Repository:
    """建一个可用于统计的仓库"""
    repo = Repository(
        owner_id=test_user.id,
        owner_type="internal",
        name=name,
        slug=f"statq-{name.lower()}-{uuid.uuid4().hex[:6]}",
        repo_type="ai",
        protocol="http",
        endpoint_url="http://127.0.0.1:9/v1/chat",
        status="approved",
    )
    db.add(repo)
    await db.flush()
    return repo


def _make_log(repo_id, user_id, hour: datetime, *, offset_h=0, status_code=200, cost="0.10", latency="120", tokens=10):
    """在某小时的第 17 分钟插入一条调用日志"""
    return APICallLog(
        repo_id=repo_id,
        user_id=user_id,
        status_code=status_code,
        cost=cost,
        response_time=latency,
        tokens_used=tokens,
        created_at=hour + timedelta(hours=offset_h, minutes=17),
    )


async def _set_watermark(db, value: datetime) -> None:
    """直接写入聚合水位（模拟后台聚合已推进到该整点）"""
    db.add(StatsAggregationState(id=_WATERMARK_ID, aggregated_until=value))
    await db.commit()


async def _live_baseline(db, start: datetime, end: datetime, repo_ids=None) -> dict:
    """
    独立基准：直接对 api_call_logs 实时统计。

    刻意用 ``FILTER`` 写法（与实现里的 CASE 写法解耦），避免"用同一表达式自证"。
    """
    conditions = [APICallLog.created_at >= start, APICallLog.created_at < end]
    if repo_ids is not None:
        conditions.append(APICallLog.repo_id.in_(repo_ids))

    stmt = select(
        func.count(APICallLog.id),
        func.count(APICallLog.id).filter(
            and_(APICallLog.status_code >= 200, APICallLog.status_code < 300)
        ),
        func.coalesce(func.sum(cast(APICallLog.cost, Numeric)), 0),
    ).where(and_(*conditions))

    row = (await db.execute(stmt)).one()
    return {
        "total_calls": int(row[0] or 0),
        "success_calls": int(row[1] or 0),
        "total_cost": Decimal(str(row[2] or 0)),
    }


def _assert_same(actual: dict, expected: dict) -> None:
    """断言两个统计结果逐值一致"""
    assert actual["total_calls"] == expected["total_calls"]
    assert actual["success_calls"] == expected["success_calls"]
    assert float(actual["total_cost"]) == pytest.approx(float(expected["total_cost"]))


class TestStatsQueryService:
    @pytest.mark.asyncio
    async def test_no_watermark_falls_back_to_live(self, db_session, test_user):
        """TC-STATQ-001: 从未聚合过（无水位）→ 整段实时查询，数值正确"""
        repo = await _make_repo(db_session, test_user, "SQ1")
        h = _hour_base()
        db_session.add_all([
            _make_log(repo.id, test_user.id, h, cost="0.10"),
            _make_log(repo.id, test_user.id, h, status_code=500, cost="0.20"),
            _make_log(repo.id, test_user.id, h, offset_h=1, cost="0.30"),
        ])
        await db_session.commit()

        svc = StatsQueryService(db_session)

        # 无水位：split_window 应返回 (None, start)
        agg_end, live_start = await svc.split_window(h, h + timedelta(hours=2))
        assert agg_end is None
        assert live_start == h

        actual = await svc.sum_metrics(h, h + timedelta(hours=2))
        expected = await _live_baseline(db_session, h, h + timedelta(hours=2))
        _assert_same(actual, expected)
        assert expected["total_calls"] == 3
        assert expected["success_calls"] == 2

    @pytest.mark.asyncio
    async def test_window_fully_covered_by_preaggregation(self, db_session, test_user):
        """TC-STATQ-002: 水位覆盖整个窗口 → 走预聚合，数值仍与实时逐值一致"""
        repo = await _make_repo(db_session, test_user, "SQ2")
        h = _hour_base()
        db_session.add_all([
            _make_log(repo.id, test_user.id, h, cost="0.10"),
            _make_log(repo.id, test_user.id, h, status_code=500, cost="0.20"),
        ])
        await db_session.commit()

        # 聚合出 repo_stats，并把水位设为该窗口上界
        await StatsAggregationService(db_session).aggregate_range(h, h + timedelta(hours=1))
        await _set_watermark(db_session, h + timedelta(hours=1))

        svc = StatsQueryService(db_session)
        agg_end, live_start = await svc.split_window(h, h + timedelta(hours=1))
        assert agg_end == h + timedelta(hours=1)   # 全部走预聚合
        assert live_start == h + timedelta(hours=1)

        actual = await svc.sum_metrics(h, h + timedelta(hours=1))
        expected = await _live_baseline(db_session, h, h + timedelta(hours=1))
        _assert_same(actual, expected)
        assert actual["total_calls"] == 2

    @pytest.mark.asyncio
    async def test_mixed_window_preaggregated_plus_live_tail(self, db_session, test_user):
        """TC-STATQ-003: 混合窗口（预聚合段 + 实时尾部）→ 与实时全量一致

        这是阶段 2 最容易出错的分支：切分点必须落在整点水位上，
        否则会把某小时的调用重复计或被漏掉。
        """
        repo = await _make_repo(db_session, test_user, "SQ3")
        h = _hour_base()
        db_session.add_all([
            _make_log(repo.id, test_user.id, h, cost="0.10"),              # 预聚合段
            _make_log(repo.id, test_user.id, h, offset_h=1, cost="0.20"),  # 预聚合段
            _make_log(repo.id, test_user.id, h, offset_h=2, cost="0.30"),  # 实时尾部
            _make_log(repo.id, test_user.id, h, offset_h=3, cost="0.40"),  # 实时尾部
        ])
        await db_session.commit()

        # 只聚合前两小时，水位 = h+2
        await StatsAggregationService(db_session).aggregate_range(h, h + timedelta(hours=2))
        await _set_watermark(db_session, h + timedelta(hours=2))

        svc = StatsQueryService(db_session)
        window_end = h + timedelta(hours=4)
        agg_end, live_start = await svc.split_window(h, window_end)
        assert agg_end == h + timedelta(hours=2)
        assert live_start == h + timedelta(hours=2)

        actual = await svc.sum_metrics(h, window_end)
        expected = await _live_baseline(db_session, h, window_end)
        _assert_same(actual, expected)
        assert expected["total_calls"] == 4
        assert float(actual["total_cost"]) == pytest.approx(1.00)

    @pytest.mark.asyncio
    async def test_repo_ids_filter_and_empty_list(self, db_session, test_user):
        """TC-STATQ-004: repo_ids 过滤；空列表 → 0（无可见仓库，不越权统计）"""
        repo_a = await _make_repo(db_session, test_user, "SQ4A")
        repo_b = await _make_repo(db_session, test_user, "SQ4B")
        h = _hour_base()
        db_session.add_all([
            _make_log(repo_a.id, test_user.id, h, cost="0.10"),
            _make_log(repo_a.id, test_user.id, h, offset_h=1, cost="0.20"),
            _make_log(repo_b.id, test_user.id, h, cost="0.50"),
        ])
        await db_session.commit()

        await StatsAggregationService(db_session).aggregate_range(h, h + timedelta(hours=2))
        await _set_watermark(db_session, h + timedelta(hours=2))

        svc = StatsQueryService(db_session)
        window_end = h + timedelta(hours=2)

        only_a = await svc.sum_metrics(h, window_end, repo_ids=[repo_a.id])
        expected_a = await _live_baseline(db_session, h, window_end, repo_ids=[repo_a.id])
        _assert_same(only_a, expected_a)
        assert only_a["total_calls"] == 2

        empty = await svc.sum_metrics(h, window_end, repo_ids=[])
        assert empty["total_calls"] == 0
        assert empty["success_calls"] == 0
        assert float(empty["total_cost"]) == 0.0

    @pytest.mark.asyncio
    async def test_distinct_users_must_be_live(self, db_session, test_user):
        """TC-STATQ-005: 独立用户数不可加 —— 同一用户跨小时不能重复计数

        若错误地用 repo_stats.unique_users 求和，这里会得到 2（错误）；
        必须实时 COUNT(DISTINCT) 得到 1。
        """
        repo = await _make_repo(db_session, test_user, "SQ5")
        h = _hour_base()
        db_session.add_all([
            _make_log(repo.id, test_user.id, h),
            _make_log(repo.id, test_user.id, h, offset_h=1),
        ])
        await db_session.commit()

        await StatsAggregationService(db_session).aggregate_range(h, h + timedelta(hours=2))
        await _set_watermark(db_session, h + timedelta(hours=2))

        # 预聚合表里确实有两行、每行 unique_users=1（说明"求和"会错）
        rows = (await db_session.execute(
            select(RepoStats).where(RepoStats.repo_id == repo.id)
        )).scalars().all()
        assert len(rows) == 2
        assert sum(r.unique_users for r in rows) == 2

        svc = StatsQueryService(db_session)
        users = await svc.count_distinct_users(h, h + timedelta(hours=2))
        assert users == 1  # 实时去重的正确值

    @pytest.mark.asyncio
    async def test_group_by_day_merges_segments(self, db_session, test_user):
        """TC-STATQ-006: 按天分组 —— 预聚合段与实时段合并后与实时分组一致"""
        repo = await _make_repo(db_session, test_user, "SQ6")
        # ⚠️ 必须用 _day_base（北京 12:00 锚）：本用例断言"跨 2 个北京自然日"，
        #    _hour_base 的 UTC 锚在北京 0~4 点窗口运行时数据会跨 3 天（实测 flaky）
        h = _day_base()
        # 第 1 天 2 条（预聚合）、第 2 天 1 条（实时尾部）
        db_session.add_all([
            _make_log(repo.id, test_user.id, h, offset_h=-1, cost="0.10"),
            _make_log(repo.id, test_user.id, h, cost="0.20"),
            _make_log(repo.id, test_user.id, h, offset_h=24, cost="0.30"),
        ])
        await db_session.commit()

        await StatsAggregationService(db_session).aggregate_range(
            h - timedelta(hours=1), h + timedelta(hours=1)
        )
        await _set_watermark(db_session, h + timedelta(hours=1))

        svc = StatsQueryService(db_session)
        rows = await svc.group_by_period(
            h - timedelta(hours=1), h + timedelta(hours=25), PERIOD_DAY
        )

        # 合并后的总调用数与实时一致
        assert sum(int(r["calls"]) for r in rows) == 3
        assert sum(float(r["cost"]) for r in rows) == pytest.approx(0.60)
        # 每天一个分组（跨 2 个自然日）
        assert len(rows) == 2

    @pytest.mark.asyncio
    async def test_group_by_hour_merges_segments(self, db_session, test_user):
        """TC-STATQ-006b: 按小时分组 —— 分段合并后每个小时的值正确"""
        repo = await _make_repo(db_session, test_user, "SQ6B")
        h = _hour_base()
        db_session.add_all([
            _make_log(repo.id, test_user.id, h, cost="0.10"),
            _make_log(repo.id, test_user.id, h, offset_h=1, cost="0.20"),
            _make_log(repo.id, test_user.id, h, offset_h=2, cost="0.30"),
        ])
        await db_session.commit()

        await StatsAggregationService(db_session).aggregate_range(h, h + timedelta(hours=1))
        await _set_watermark(db_session, h + timedelta(hours=1))

        svc = StatsQueryService(db_session)
        rows = await svc.group_by_period(h, h + timedelta(hours=3), PERIOD_HOUR)

        assert len(rows) == 3
        assert [int(r["calls"]) for r in rows] == [1, 1, 1]
        assert sum(float(r["cost"]) for r in rows) == pytest.approx(0.60)

    @pytest.mark.asyncio
    async def test_group_by_repo_merges_segments(self, db_session, test_user):
        """TC-STATQ-007: 按仓库分组 —— 分段合并后各仓库值正确"""
        repo_a = await _make_repo(db_session, test_user, "SQ7A")
        repo_b = await _make_repo(db_session, test_user, "SQ7B")
        h = _hour_base()
        db_session.add_all([
            _make_log(repo_a.id, test_user.id, h, cost="0.10"),               # 预聚合段
            _make_log(repo_a.id, test_user.id, h, offset_h=2, cost="0.20"),   # 实时尾部
            _make_log(repo_b.id, test_user.id, h, offset_h=2, status_code=500, cost="0.40"),
        ])
        await db_session.commit()

        await StatsAggregationService(db_session).aggregate_range(h, h + timedelta(hours=1))
        await _set_watermark(db_session, h + timedelta(hours=1))

        svc = StatsQueryService(db_session)
        metrics = await svc.group_by_repo(h, h + timedelta(hours=3))

        assert metrics[repo_a.id]["total_calls"] == 2
        assert metrics[repo_a.id]["success_calls"] == 2
        assert float(metrics[repo_a.id]["total_cost"]) == pytest.approx(0.30)

        assert metrics[repo_b.id]["total_calls"] == 1
        assert metrics[repo_b.id]["success_calls"] == 0      # 500 不算成功
        assert float(metrics[repo_b.id]["total_cost"]) == pytest.approx(0.40)

    @pytest.mark.asyncio
    async def test_watermark_initialized_from_earliest_log(self, db_session, test_user):
        """TC-STATQ-008: 首次聚合 —— 水位从"最早日志所在整点"初始化并推进到当前整点"""
        repo = await _make_repo(db_session, test_user, "SQ8")
        h = _hour_base()
        db_session.add(_make_log(repo.id, test_user.id, h))
        await db_session.commit()

        svc = StatsAggregationService(db_session)
        result = await svc.aggregate_until_now()

        assert result["remaining_hours"] == 0
        state = (await db_session.execute(
            select(StatsAggregationState).where(StatsAggregationState.id == _WATERMARK_ID)
        )).scalar_one()
        current_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        assert state.aggregated_until == current_hour

        # 水位之后没有任何"未聚合空洞"：repo_stats 应包含该小时
        stats_rows = (await db_session.execute(
            select(RepoStats).where(RepoStats.repo_id == repo.id)
        )).scalars().all()
        assert {r.stat_hour for r in stats_rows} == {h}

    @pytest.mark.asyncio
    async def test_catchup_is_batched(self, db_session, test_user):
        """TC-STATQ-009: 历史回填分批推进 —— 单轮不超过 max_hours_per_run，剩余量可观测"""
        repo = await _make_repo(db_session, test_user, "SQ9")
        h = _hour_base()
        # 跨 4 个小时的日志
        db_session.add_all([
            _make_log(repo.id, test_user.id, h, offset_h=i) for i in range(4)
        ])
        await db_session.commit()

        svc = StatsAggregationService(db_session)
        first = await svc.aggregate_until_now(max_hours_per_run=2)

        # 第一轮最多 2 小时，且一定还有剩余（h 距当前整点 3 小时）
        assert first["hours"] == 2
        assert first["remaining_hours"] >= 1

        state = (await db_session.execute(
            select(StatsAggregationState).where(StatsAggregationState.id == _WATERMARK_ID)
        )).scalar_one()
        assert state.aggregated_until == h + timedelta(hours=2)

        # 继续追赶直至追平
        second = await svc.aggregate_until_now(max_hours_per_run=100)
        assert second["remaining_hours"] == 0

    @pytest.mark.asyncio
    async def test_watermark_never_moves_backwards(self, db_session, test_user):
        """TC-STATQ-010: 水位只增不减 —— 重复执行不会把已聚合范围"缩回"（否则读侧会漏算）"""
        repo = await _make_repo(db_session, test_user, "SQ10")
        h = _hour_base()
        db_session.add(_make_log(repo.id, test_user.id, h))
        await db_session.commit()

        svc = StatsAggregationService(db_session)
        await svc.aggregate_until_now()
        advanced = await svc.get_watermark()

        # 强行回退
        await svc._advance_watermark(h)

        assert await svc.get_watermark() == advanced

    @pytest.mark.asyncio
    async def test_success_definition_is_2xx(self, db_session, test_user):
        """TC-STATQ-011: 成功口径统一为 2xx —— 3xx 不算成功（预聚合与实时一致）"""
        repo = await _make_repo(db_session, test_user, "SQ11")
        h = _hour_base()
        db_session.add_all([
            _make_log(repo.id, test_user.id, h, status_code=200),
            _make_log(repo.id, test_user.id, h, status_code=302),   # 3xx：不算成功
            _make_log(repo.id, test_user.id, h, status_code=500),
        ])
        await db_session.commit()

        await StatsAggregationService(db_session).aggregate_range(h, h + timedelta(hours=1))
        await _set_watermark(db_session, h + timedelta(hours=1))

        stat = (await db_session.execute(
            select(RepoStats).where(RepoStats.repo_id == repo.id)
        )).scalar_one()
        assert stat.success_calls == 1        # 只有 200 算成功
        assert stat.failed_calls == 2

        svc = StatsQueryService(db_session)
        actual = await svc.sum_metrics(h, h + timedelta(hours=1))
        expected = await _live_baseline(db_session, h, h + timedelta(hours=1))
        _assert_same(actual, expected)
        assert actual["success_calls"] == 1

    @pytest.mark.asyncio
    async def test_empty_and_inverted_window(self, db_session, test_user):
        """TC-STATQ-012: 边界 —— 空窗口/倒置窗口返回 0，不抛异常"""
        svc = StatsQueryService(db_session)
        h = _hour_base()

        empty = await svc.sum_metrics(h, h)
        assert empty == {"total_calls": 0, "success_calls": 0, "total_cost": Decimal("0")}

        inverted = await svc.sum_metrics(h + timedelta(hours=1), h)
        assert inverted["total_calls"] == 0

        assert await svc.count_distinct_users(h, h) == 0
        assert await svc.group_by_period(h, h, PERIOD_DAY) == []
        assert await svc.group_by_repo(h, h) == {}

        with pytest.raises(ValueError):
            await svc.group_by_period(h, h + timedelta(hours=1), "minute")
