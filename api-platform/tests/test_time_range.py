"""
时区口径统一测试 —— 「北京时间业务口径 ↔ UTC 存储」

验证 `src/utils/time_range.py` 的各转换函数，并以**落库级**用例证明：
    北京日界（半开区间）与 UTC 日界对同一条记录的归属判定不同 ——
    这正是 2026-09-15 查询侧口径收敛（func.date → 半开区间 / cst_date_expr）的依据。

对应文档：docs/TIMEZONE_DESIGN.md
用例编号：TC-TZ-001 ~ TC-TZ-008
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from src.utils.time_range import (
    CST,
    cst_date_expr,
    cst_day_range_utc,
    cst_day_range_utc_from_date,
    cst_day_start_utc,
    cst_month_range_utc,
    cst_now,
    utc_now,
)

# ==================== 1. 区间转换函数（单元） ====================


class TestCstDayRange:
    def test_day_range_from_date_is_half_open_utc(self):
        """TC-TZ-001: 北京某日 [00:00, 次日00:00) 半开区间 = 对应 UTC 区间

        北京 2026-09-15 00:00 = UTC 2026-09-14 16:00（UTC+8 固定偏移，无夏令时）
        """
        start, end = cst_day_range_utc_from_date(date(2026, 9, 15))

        assert start == datetime(2026, 9, 14, 16, 0, 0, tzinfo=timezone.utc)
        assert end == datetime(2026, 9, 15, 16, 0, 0, tzinfo=timezone.utc)
        # 半开区间：长度精确 1 天（不丢亚秒，与旧 <= 23:59:59 闭区间的本质区别）
        assert end - start == timedelta(days=1)

    def test_day_range_consistent_between_two_apis(self):
        """TC-TZ-002: cst_day_range_utc(days_ago) 与 from_date(同一天) 结果一致"""
        target = (cst_now() - timedelta(days=3)).date()

        start_a, end_a = cst_day_range_utc(days_ago=3)
        start_b, end_b = cst_day_range_utc_from_date(target)

        assert (start_a, end_a) == (start_b, end_b)

    def test_day_start_utc(self):
        """TC-TZ-003: cst_day_start_utc(days_ago=N) = 北京 N 天前 00:00 的 UTC 时刻"""
        assert cst_day_start_utc() == cst_day_range_utc(days_ago=0)[0]
        assert cst_day_start_utc(days_ago=2) == cst_day_range_utc(days_ago=2)[0]

    def test_month_range(self):
        """TC-TZ-004: 北京某自然月 [1日00:00, 次月1日00:00) 的 UTC 区间"""
        start, end = cst_month_range_utc(2026, 9)

        assert start == datetime(2026, 8, 31, 16, 0, 0, tzinfo=timezone.utc)
        assert end == datetime(2026, 9, 30, 16, 0, 0, tzinfo=timezone.utc)

    def test_values_are_aware(self):
        """TC-TZ-005: 所有返回值必须是 aware（naive 与 timestamptz 比较会出错/偏移）"""
        for dt in (*cst_day_range_utc(), *cst_month_range_utc(2026, 1), cst_now(), utc_now()):
            assert dt.tzinfo is not None


# ==================== 2. 分组表达式（SQL 编译验证） ====================


class TestCstDateExpr:
    def test_expr_uses_explicit_timezone(self):
        """TC-TZ-006: 生成的 SQL 显式含 Asia/Shanghai（不依赖会话时区）"""
        from src.models.billing import Bill

        sql = str(cst_date_expr(Bill.created_at).compile(compile_kwargs={"literal_binds": True}))

        assert "Asia/Shanghai" in sql
        assert "timezone" in sql


# ==================== 3. 落库级验证（数据库记录级） ====================


class TestTimezoneBoundaryPersistence:
    """
    用同一条记录证明「北京日界 ≠ UTC 日界」——口径收敛的落库依据。

    构造：created_at = UTC 2026-09-14 20:00 = 北京 2026-09-15 04:00
    预期：按**北京日界**归入 9-15；按 **UTC 日界**归入 9-14（旧口径的错误归属）。
    """

    _BILL_NO = "TEST_TZ_BOUNDARY_0001"
    _UTC_INSTANT = datetime(2026, 9, 14, 20, 0, 0, tzinfo=timezone.utc)

    async def _insert_bill(self, db_session, test_user):
        from src.models.billing import Bill

        bill = Bill(
            user_id=test_user.id,
            bill_no=self._BILL_NO,
            bill_type="recharge",
            amount="1.0",
            balance_before="0",
            balance_after="1.0",
            created_at=self._UTC_INSTANT,
        )
        db_session.add(bill)
        await db_session.commit()
        return bill

    @pytest.mark.asyncio
    async def test_record_belongs_to_beijing_day_not_utc_day(self, db_session, test_user):
        """TC-TZ-007: 半开区间（北京日界）命中；同一天的 UTC 日界区间不命中"""
        from src.models.billing import Bill

        await self._insert_bill(db_session, test_user)

        async def _count(start: datetime, end: datetime) -> int:
            rows = (
                await db_session.execute(
                    select(Bill).where(
                        Bill.bill_no == self._BILL_NO,
                        Bill.created_at >= start,
                        Bill.created_at < end,
                    )
                )
            ).scalars().all()
            return len(rows)

        # 北京 9-15 的窗口 [9-14 16:00 UTC, 9-15 16:00 UTC) → 命中
        start_cst, end_cst = cst_day_range_utc_from_date(date(2026, 9, 15))
        assert await _count(start_cst, end_cst) == 1

        # **同一日期标签"9-15"** 的 UTC 日界窗口 [9-15 00:00 UTC, 9-16 00:00 UTC) → 不命中
        # （旧口径 func.date(...) == date(2026,9,15) 按会话时区 UTC 取日期，
        #   这条记录会被归入"9-14"—— 用户查 9-15 时该记录丢失）
        start_utc = datetime(2026, 9, 15, 0, 0, 0, tzinfo=timezone.utc)
        end_utc = datetime(2026, 9, 16, 0, 0, 0, tzinfo=timezone.utc)
        assert await _count(start_utc, end_utc) == 0

    @pytest.mark.asyncio
    async def test_group_by_uses_beijing_date(self, db_session, test_user):
        """TC-TZ-008: cst_date_expr 分组返回**北京日期** 9-15（原 func.date 返回 UTC 9-14）"""
        from src.models.billing import Bill

        await self._insert_bill(db_session, test_user)

        rows = (
            await db_session.execute(
                select(cst_date_expr(Bill.created_at)).where(
                    Bill.bill_no == self._BILL_NO
                )
            )
        ).scalars().all()

        assert rows == [date(2026, 9, 15)]
