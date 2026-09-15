"""
统计预聚合测试（P1-6）—— api_call_logs → repo_stats 小时级聚合

覆盖（落库级，backlog §3.2 验收标准：聚合任务幂等）：
1. 单小时聚合（成功/失败、成本、时延、tokens）
2. 跨小时 / 多仓库分组
3. **幂等**：重复执行行数与值不变（唯一约束 + upsert 覆盖）
4. 空区间安全
5. 唯一约束存在（防模型回退）

用例编号：TC-STAT-001 ~ TC-STAT-006
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from src.config.settings import settings as global_settings
from src.models.billing import APICallLog
from src.models.repository import Repository, RepoStats
from src.services.stats_aggregation_service import StatsAggregationService


def _hour_base() -> datetime:
    """对齐到 UTC 当前整点，再往前推 2 小时（避免与"当前小时"边界竞争）"""
    now = datetime.now(timezone.utc)
    return (now - timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)


async def _make_repo(db_session, test_user, name: str) -> Repository:
    repo = Repository(
        owner_id=test_user.id,
        owner_type="internal",
        name=name,
        slug=f"stat-{name.lower()}-{uuid.uuid4().hex[:6]}",
        repo_type="ai",
        protocol="http",
        endpoint_url="http://127.0.0.1:9/v1/chat",
        status="approved",
    )
    db_session.add(repo)
    await db_session.flush()
    return repo


def _make_log(repo_id, user_id, hour_base: datetime, *, offset_h: int = 0, status_code=200, cost="0.10", latency="120", tokens=10):
    return APICallLog(
        repo_id=repo_id,
        user_id=user_id,
        status_code=status_code,
        cost=cost,
        response_time=latency,
        tokens_used=tokens,
        created_at=hour_base + timedelta(hours=offset_h, minutes=17),
    )


@pytest.fixture
def service(db_session) -> StatsAggregationService:
    return StatsAggregationService(db_session)


class TestStatsAggregation:
    @pytest.mark.asyncio
    async def test_single_hour_aggregation(self, db_session, test_user, service):
        """TC-STAT-001: 单小时聚合 —— 计数/成败/成本/时延/tokens 正确"""
        repo = await _make_repo(db_session, test_user, "STAT1")
        h = _hour_base()

        db_session.add_all([
            _make_log(repo.id, test_user.id, h, status_code=200, cost="0.10", latency="100", tokens=5),
            _make_log(repo.id, test_user.id, h, status_code=200, cost="0.30", latency="200", tokens=7),
            _make_log(repo.id, test_user.id, h, status_code=500, cost="0.00", latency="50", tokens=1),
        ])
        await db_session.commit()

        result = await service.aggregate_range(h, h + timedelta(hours=1))
        assert result["upserted"] == 1

        rows = (await db_session.execute(
            select(RepoStats).where(RepoStats.repo_id == repo.id)
        )).scalars().all()
        assert len(rows) == 1
        stat = rows[0]
        assert stat.total_calls == 3
        assert stat.success_calls == 2
        assert stat.failed_calls == 1
        assert stat.total_tokens == 13
        assert float(stat.total_cost) == pytest.approx(0.40)
        assert stat.avg_latency_ms is not None
        assert stat.stat_hour == h  # UTC 整点对齐

    @pytest.mark.asyncio
    async def test_multiple_hours_and_repos(self, db_session, test_user, service):
        """TC-STAT-002: 跨小时 + 多仓库 → 按 (repo, hour) 正确分组"""
        repo_a = await _make_repo(db_session, test_user, "STATA")
        repo_b = await _make_repo(db_session, test_user, "STATB")
        h = _hour_base()

        db_session.add_all([
            _make_log(repo_a.id, test_user.id, h),
            _make_log(repo_a.id, test_user.id, h, offset_h=1),
            _make_log(repo_b.id, test_user.id, h),
        ])
        await db_session.commit()

        result = await service.aggregate_range(h, h + timedelta(hours=2))
        assert result["upserted"] == 3  # A×2 小时 + B×1 小时

        hours_a = (await db_session.execute(
            select(RepoStats).where(RepoStats.repo_id == repo_a.id)
        )).scalars().all()
        assert {s.stat_hour for s in hours_a} == {h, h + timedelta(hours=1)}

    @pytest.mark.asyncio
    async def test_idempotent_rerun(self, db_session, test_user, service):
        """TC-STAT-003: 幂等 —— 重复聚合行数与值不变（唯一约束 + upsert 覆盖）"""
        repo = await _make_repo(db_session, test_user, "STATID")
        h = _hour_base()

        db_session.add(_make_log(repo.id, test_user.id, h, cost="0.50"))
        await db_session.commit()

        first = await service.aggregate_range(h, h + timedelta(hours=1))
        assert first["upserted"] == 1

        # 第二次执行（同一窗口重复聚合）
        second = await service.aggregate_range(h, h + timedelta(hours=1))
        assert second["upserted"] == 1

        rows = (await db_session.execute(
            select(RepoStats).where(RepoStats.repo_id == repo.id)
        )).scalars().all()
        assert len(rows) == 1                      # 不产生重复行
        assert rows[0].total_calls == 1            # 值不被累加污染
        assert float(rows[0].total_cost) == pytest.approx(0.50)

    @pytest.mark.asyncio
    async def test_empty_range_is_safe(self, db_session, test_user, service):
        """TC-STAT-004: 无日志的区间 → 0 行、不报错"""
        h = _hour_base()
        result = await service.aggregate_range(h, h + timedelta(hours=1))
        assert result == {"hours": 1, "upserted": 0}

    @pytest.mark.asyncio
    async def test_unique_constraint_exists(self, db_session):
        """TC-STAT-005: repo_stats 有 (repo_id, stat_hour) 唯一约束（防模型回退）"""
        constraints = [
            c.name for c in RepoStats.__table__.constraints if c.name
        ]
        assert "uq_repo_stats_repo_hour" in constraints

        # 数据库侧确认
        from sqlalchemy import text
        result = await db_session.execute(text(
            "SELECT conname FROM pg_constraint WHERE conname='uq_repo_stats_repo_hour'"
        ))
        assert result.scalar() == "uq_repo_stats_repo_hour"

    @pytest.mark.asyncio
    async def test_aggregate_recent_hours_bounds(self, db_session, test_user, service):
        """TC-STAT-006: recent_hours 窗口 —— 当前整点之前的完整小时被聚合"""
        repo = await _make_repo(db_session, test_user, "STATRC")
        h = _hour_base()  # = 当前整点 - 2h，位于默认窗口 [now_hour-2, now_hour) 内

        db_session.add(_make_log(repo.id, test_user.id, h))
        await db_session.commit()

        result = await service.aggregate_recent_hours(hours=2)
        assert result["upserted"] >= 1

        rows = (await db_session.execute(
            select(RepoStats).where(RepoStats.repo_id == repo.id)
        )).scalars().all()
        assert len(rows) == 1
        assert rows[0].stat_hour == h
