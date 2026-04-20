"""
阶段三：定时对账与报表导出 测试脚本

测试以下接口：
1. GET /admin/reconciliation/scheduler/status - 获取调度器状态
2. POST /admin/reconciliation/scheduler/trigger - 手动触发对账
3. POST /admin/reconciliation/report - 生成对账报表
4. GET /admin/reconciliation/report/download - 下载报表
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete, and_
from src.config.database import AsyncSessionLocal
from src.models import User, Bill, PlatformAccount, ReconciliationRecord, ReconciliationDispute
from src.api.v1.admin_reconciliation import (
    get_scheduler_status,
    trigger_reconciliation,
    generate_reconciliation_report,
    TriggerReconciliationRequest,
    ReconciliationReportRequest,
)
import uuid

# 模拟管理员用户
MOCK_ADMIN_USER = {
    "id": str(uuid.uuid4()),
    "username": "test_admin",
    "email": "admin@test.com",
    "role": "admin",
}


async def setup_test_data():
    """准备测试数据"""
    print("\n" + "=" * 60)
    print("[SETUP] 准备测试数据...")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        # 清理旧数据
        await db.execute(delete(User).where(User.email == "test_scheduler@example.com"))
        await db.execute(delete(ReconciliationDispute))
        await db.execute(delete(ReconciliationRecord))
        await db.commit()
        
        # 创建测试用户
        test_user = User(
            id=uuid.uuid4(),
            username="test_user_scheduler",
            email="test_scheduler@example.com",
            phone="13900000000",
            password_hash="test_hash",
            user_status="active",
        )
        db.add(test_user)
        await db.flush()
        
        # 创建多日测试数据（最近7天）
        for day_offset in range(7):
            test_date = datetime.utcnow() - timedelta(days=day_offset)
            
            # 支付宝充值
            bill = Bill(
                user_id=test_user.id,
                bill_no=f"SCHED_TEST_{test_date.strftime('%Y%m%d')}_001",
                bill_type="recharge",
                amount=str(100.00 + day_offset * 10),
                balance_before="1000.00",
                balance_after=str(1100.00 + day_offset * 10),
                payment_method="alipay",
                status="completed",
                transaction_id=f"TXN_SCHED_{test_date.strftime('%Y%m%d')}_001",
                environment="simulation",
            )
            db.add(bill)
            
            # 微信充值
            bill2 = Bill(
                user_id=test_user.id,
                bill_no=f"SCHED_TEST_{test_date.strftime('%Y%m%d')}_002",
                bill_type="recharge",
                amount=str(50.00 + day_offset * 5),
                balance_before="500.00",
                balance_after=str(550.00 + day_offset * 5),
                payment_method="wechat",
                status="completed",
                transaction_id=f"TXN_SCHED_{test_date.strftime('%Y%m%d')}_002",
                environment="simulation",
            )
            db.add(bill2)
        
        await db.commit()
        print(f"[OK] 创建测试用户: {test_user.username}")
        print(f"[OK] 创建14笔充值账单（7天 x 2渠道）")


async def cleanup_test_data():
    """清理测试数据"""
    print("\n" + "=" * 60)
    print("[CLEANUP] 清理测试数据...")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.email == "test_scheduler@example.com"))
        await db.execute(delete(ReconciliationDispute))
        await db.execute(delete(ReconciliationRecord))
        await db.commit()
        print("[OK] 清理完成")


async def test_scheduler_status():
    """测试1: 获取调度器状态"""
    print("\n" + "=" * 60)
    print("[TEST 1] GET /admin/reconciliation/scheduler/status")
    print("=" * 60)
    
    try:
        result = await get_scheduler_status(current_user=MOCK_ADMIN_USER)
        data = result.data
        
        print(f"\n[RESULT]")
        print(f"   - 是否运行中: {data.is_running}")
        print(f"   - 上次运行时间: {data.last_run_time or '从未运行'}")
        print(f"   - 任务记录数: {data.task_count}")
        
        print(f"\n[TEST 1 PASSED]")
        return True
    except Exception as e:
        print(f"\n[TEST 1 FAILED] {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_trigger_reconciliation():
    """测试2: 手动触发对账"""
    print("\n" + "=" * 60)
    print("[TEST 2] POST /admin/reconciliation/scheduler/trigger")
    print("=" * 60)
    
    # 使用昨天作为对账日期
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    try:
        request = TriggerReconciliationRequest(
            date=yesterday,
            channels=["alipay", "wechat"]
        )
        
        result = await trigger_reconciliation(
            request=request,
            current_user=MOCK_ADMIN_USER,
        )
        data = result.data
        
        print(f"\n[REQUEST]")
        print(f"   - 对账日期: {yesterday}")
        print(f"   - 渠道: alipay, wechat")
        
        print(f"\n[RESULT]")
        print(f"   - 状态: {data.status}")
        print(f"   - 执行时间: {data.executed_at}")
        print(f"   - 总平台交易: {data.total.get('platform_trade_count', 0)} 笔")
        print(f"   - 总渠道交易: {data.total.get('channel_trade_count', 0)} 笔")
        print(f"   - 匹配数: {data.total.get('match_count', 0)} 笔")
        
        if "alipay" in data.channels:
            print(f"\n[渠道详情 - 支付宝]")
            ch = data.channels["alipay"]
            print(f"   - 平台: {ch.get('platform_trade_count', 0)}笔 / {ch.get('platform_trade_amount', 0):.2f}")
            print(f"   - 渠道: {ch.get('channel_trade_count', 0)}笔 / {ch.get('channel_trade_amount', 0):.2f}")
        
        if "wechat" in data.channels:
            print(f"\n[渠道详情 - 微信]")
            ch = data.channels["wechat"]
            print(f"   - 平台: {ch.get('platform_trade_count', 0)}笔 / {ch.get('platform_trade_amount', 0):.2f}")
        
        print(f"\n[TEST 2 PASSED]")
        return True
    except Exception as e:
        print(f"\n[TEST 2 FAILED] {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_generate_report():
    """测试3: 生成对账报表"""
    print("\n" + "=" * 60)
    print("[TEST 3] POST /admin/reconciliation/report")
    print("=" * 60)
    
    # 查询最近7天
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    try:
        request = ReconciliationReportRequest(
            start_date=start_date,
            end_date=end_date,
            channel=None,  # 所有渠道
        )
        
        async with AsyncSessionLocal() as db:
            result = await generate_reconciliation_report(
                request=request,
                db=db,
                current_user=MOCK_ADMIN_USER,
            )
            data = result.data
        
        print(f"\n[REQUEST]")
        print(f"   - 日期范围: {start_date} ~ {end_date}")
        print(f"   - 渠道: 全部")
        
        print(f"\n[RESULT]")
        print(f"   - 报表记录数: {len(data.items)}")
        print(f"   - 生成时间: {data.generated_at}")
        
        if data.summary:
            print(f"\n[汇总统计]")
            print(f"   - 对账天数: {data.summary.get('total_count', 0)}")
            print(f"   - 总平台金额: {data.summary.get('total_platform_amount', 0):.2f}")
            print(f"   - 总渠道金额: {data.summary.get('total_channel_amount', 0):.2f}")
            print(f"   - 总匹配数: {data.summary.get('total_match_count', 0)}")
            print(f"   - 待处理差异: {data.summary.get('total_pending', 0)}")
        
        if data.items:
            print(f"\n[报表预览 - 前3条]")
            for i, item in enumerate(data.items[:3], 1):
                print(f"   [{i}] {item.reconcile_date} | {item.channel_name}")
                print(f"       平台: {item.platform_trade_count} | 渠道: {item.channel_trade_count} | 匹配率: {item.match_rate}%")
        
        print(f"\n[TEST 3 PASSED]")
        return True
    except Exception as e:
        print(f"\n[TEST 3 FAILED] {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_scheduler_status_after():
    """测试4: 再次检查调度器状态"""
    print("\n" + "=" * 60)
    print("[TEST 4] GET /admin/reconciliation/scheduler/status (After trigger)")
    print("=" * 60)
    
    try:
        result = await get_scheduler_status(current_user=MOCK_ADMIN_USER)
        data = result.data
        
        print(f"\n[RESULT]")
        print(f"   - 是否运行中: {data.is_running}")
        print(f"   - 上次运行时间: {data.last_run_time or '从未运行'}")
        print(f"   - 任务记录数: {data.task_count}")
        
        if data.tasks:
            print(f"\n[最近任务]")
            for task in data.tasks[:3]:
                print(f"   - ID: {task['id']} | 日期: {task['date']} | 状态: {task['status']}")
        
        print(f"\n[TEST 4 PASSED]")
        return True
    except Exception as e:
        print(f"\n[TEST 4 FAILED] {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("STAGE 3: SCHEDULER & REPORT API TEST")
    print("=" * 60)
    print(f"Test Time: {datetime.utcnow().isoformat()}")
    
    # 准备测试数据
    await setup_test_data()
    
    # 执行测试
    results = {}
    
    results["获取调度器状态"] = await test_scheduler_status()
    results["手动触发对账"] = await test_trigger_reconciliation()
    results["生成对账报表"] = await test_generate_report()
    results["再次检查状态"] = await test_scheduler_status_after()
    
    # 打印测试结果汇总
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"   {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED!")
    print("=" * 60)
    
    # 清理测试数据
    await cleanup_test_data()
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
