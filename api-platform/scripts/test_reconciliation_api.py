"""
对账API接口测试脚本

测试以下接口：
1. POST /admin/reconciliation/execute - 执行对账
2. GET /admin/reconciliation/result - 对账结果查询
3. GET /admin/reconciliation/disputes - 差异记录列表
4. PUT /admin/reconciliation/disputes/{id} - 处理差异
5. GET /admin/reconciliation/history - 历史对账记录
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete, and_
from src.config.database import AsyncSessionLocal, Base
from src.config.database import async_engine
from src.models import User, Bill, Account, PlatformAccount, ReconciliationRecord, ReconciliationDispute
from src.models.billing import Bill
from src.api.v1.admin_reconciliation import (
    execute_reconciliation,
    get_reconciliation_result,
    get_reconciliation_disputes,
    handle_reconciliation_dispute,
    get_reconciliation_history,
    ExecuteReconciliationRequest,
    HandleDisputeRequest,
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
        # 先清理同名测试用户
        from src.models.user import User
        await db.execute(delete(User).where(User.email == "test_recon@example.com"))
        await db.commit()
        
        # 创建测试用户
        test_user = User(
            id=uuid.uuid4(),
            username="test_user_recon",
            email="test_recon@example.com",
            phone="13800138000",
            password_hash="hashed_password_here",
            user_status="active",
        )
        db.add(test_user)
        
        # 创建用户账户
        test_account = Account(
            id=uuid.uuid4(),
            user_id=test_user.id,
            account_type="balance",
            balance="1000.00",
            frozen_balance="0.00",
            total_recharge="1000.00",
            total_consume="0.00",
        )
        db.add(test_account)
        
        # 创建充值账单（今天的多笔充值）
        today = datetime.utcnow()
        bills_data = [
            {"amount": 100.00, "payment_method": "alipay", "status": "completed"},
            {"amount": 200.00, "payment_method": "alipay", "status": "completed"},
            {"amount": 50.00, "payment_method": "alipay", "status": "completed"},
            {"amount": 150.00, "payment_method": "wechat", "status": "completed"},
            {"amount": 300.00, "payment_method": "wechat", "status": "completed"},
            {"amount": 80.00, "payment_method": "bankcard", "status": "completed"},
        ]
        
        for i, bill_data in enumerate(bills_data):
            bill = Bill(
                user_id=test_user.id,
                bill_no=f"TEST_RECON_{today.strftime('%Y%m%d')}_{i+1:03d}",
                bill_type="recharge",
                amount=str(bill_data["amount"]),
                balance_before="1000.00" if i == 0 else str(1100.00 + (i-1) * 250),
                balance_after=str(1100.00 + i * 250),
                payment_method=bill_data["payment_method"],
                status=bill_data["status"],
                transaction_id=f"TXN_TEST_{today.strftime('%Y%m%d%H%M%S')}_{i+1}",
                environment="simulation",
                description=f"测试充值 {bill_data['amount']} 元",
            )
            db.add(bill)
        
        # 创建平台账户
        for channel in ["alipay", "wechat", "bankcard"]:
            account = PlatformAccount(
                id=uuid.uuid4(),
                channel=channel,
                account_name=f"测试{channel}账户",
                balance=Decimal("0.00"),
                currency="CNY",
                status="active",
            )
            db.add(account)
        
        await db.commit()
        print(f"[OK] 创建测试用户: {test_user.username}")
        print(f"[OK] 创建6笔充值账单（支付宝3笔，微信2笔，银行卡1笔）")
        print(f"[OK] 创建3个平台账户")


async def cleanup_test_data():
    """清理测试数据"""
    print("\n" + "=" * 60)
    print("[CLEANUP] 清理测试数据...")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        # 删除对账记录
        await db.execute(delete(ReconciliationDispute))
        await db.execute(delete(ReconciliationRecord))
        await db.commit()
        
        # 删除测试账单
        await db.execute(delete(Bill).where(Bill.bill_no.like("TEST_RECON_%")))
        await db.commit()
        
        print("[OK] 清理完成")


async def test_1_execute_reconciliation():
    """测试1: 执行对账"""
    print("\n" + "=" * 60)
    print("[TEST 1] POST /admin/reconciliation/execute - 执行对账")
    print("=" * 60)
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    async with AsyncSessionLocal() as db:
        try:
            request = ExecuteReconciliationRequest(
                date=today,
                channel="alipay"
            )
            response = await execute_reconciliation(
                request=request,
                db=db,
                current_user=MOCK_ADMIN_USER,
            )
            
            print(f"\n[REQUEST]")
            print(f"   - 日期: {today}")
            print(f"   - 渠道: alipay")
            
            print(f"\n[RESULT]")
            data = response.data
            print(f"   - 对账ID: {data.reconciliation_id}")
            print(f"   - 本地交易笔数: {data.platform_trade_count}")
            print(f"   - 本地交易金额: {data.platform_trade_amount:.2f}")
            print(f"   - 第三方交易笔数: {data.channel_trade_count}")
            print(f"   - 第三方交易金额: {data.channel_trade_amount:.2f}")
            print(f"   - 匹配笔数: {data.match_count}")
            print(f"   - 匹配金额: {data.match_amount:.2f}")
            print(f"   - 长款笔数: {data.long_count}")
            print(f"   - 长款金额: {data.long_amount:.2f}")
            print(f"   - 短款笔数: {data.short_count}")
            print(f"   - 金额差异笔数: {data.amount_diff_count}")
            print(f"   - 状态: {data.status}")
            
            print(f"\n[TEST 1 PASSED]")
            return data.reconciliation_id
        except Exception as e:
            print(f"\n[TEST 1 FAILED] {str(e)}")
            import traceback
            traceback.print_exc()
            return None


async def test_2_get_reconciliation_result(reconciliation_id: str):
    """测试2: 对账结果查询"""
    print("\n" + "=" * 60)
    print("[TEST 2] GET /admin/reconciliation/result - 对账结果查询")
    print("=" * 60)
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    async with AsyncSessionLocal() as db:
        try:
            response = await get_reconciliation_result(
                db=db,
                current_user=MOCK_ADMIN_USER,
                date=today,
                channel="alipay",
            )
            
            print(f"\n[REQUEST]")
            print(f"   - 日期: {today}")
            print(f"   - 渠道: alipay")
            
            print(f"\n[RESULT]")
            data = response.data
            print(f"   - 对账ID: {data.id}")
            print(f"   - 对账日期: {data.reconcile_date}")
            print(f"   - 渠道: {data.channel}")
            print(f"   - 本地交易: {data.platform_trade_count}笔 / {data.platform_trade_amount:.2f}")
            print(f"   - 第三方交易: {data.channel_trade_count}笔 / {data.channel_trade_amount:.2f}")
            print(f"   - 匹配: {data.match_count}笔 / {data.match_amount:.2f}")
            print(f"   - 长款: {data.long_count}笔 / {data.long_amount:.2f}")
            print(f"   - 短款: {data.short_count}笔 / {data.short_amount:.2f}")
            print(f"   - 金额差异: {data.amount_diff_count}笔 / {data.amount_diff_total:.2f}")
            print(f"   - 状态: {data.status}")
            
            print(f"\n[TEST 2 PASSED]")
            return True
        except Exception as e:
            print(f"\n[TEST 2 FAILED] {str(e)}")
            import traceback
            traceback.print_exc()
            return False


async def test_3_get_disputes():
    """测试3: 差异记录列表"""
    print("\n" + "=" * 60)
    print("[TEST 3] GET /admin/reconciliation/disputes - 差异记录列表")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        try:
            response = await get_reconciliation_disputes(
                db=db,
                current_user=MOCK_ADMIN_USER,
                dispute_type=None,
                handle_status=None,
                page=1,
                page_size=20,
            )
            
            print(f"\n[RESULT]")
            data = response.data
            print(f"   - 总记录数: {data.pagination['total']}")
            print(f"   - 当前页: {data.pagination['page']} / 总页数: {data.pagination['total_pages']}")
            
            if data.items:
                print(f"\n   差异明细:")
                for i, item in enumerate(data.items[:3], 1):
                    print(f"   [{i}] {item.dispute_type} | 订单: {item.local_order_no or 'N/A'} | 差异金额: {item.diff_amount or 0:.2f} | 状态: {item.handle_status}")
            
            print(f"\n[TEST 3 PASSED]")
            return data.items[0].id if data.items else None
        except Exception as e:
            print(f"\n[TEST 3 FAILED] {str(e)}")
            import traceback
            traceback.print_exc()
            return None


async def test_4_handle_dispute(dispute_id: str):
    """测试4: 处理差异"""
    print("\n" + "=" * 60)
    print("[TEST 4] PUT /admin/reconciliation/disputes/{id} - 处理差异")
    print("=" * 60)
    
    if not dispute_id:
        print("[SKIP] 无差异记录可测试，跳过此测试")
        return True
    
    async with AsyncSessionLocal() as db:
        try:
            request = HandleDisputeRequest(
                handle_status="resolved",
                handle_remark="已核实为测试数据，无需处理",
                reason="测试",
            )
            
            print(f"\n[REQUEST]")
            print(f"   - 差异ID: {dispute_id}")
            print(f"   - 处理状态: resolved")
            print(f"   - 处理备注: 已核实为测试数据，无需处理")
            
            response = await handle_reconciliation_dispute(
                dispute_id=dispute_id,
                request=request,
                db=db,
                current_user=MOCK_ADMIN_USER,
            )
            
            print(f"\n[RESULT]")
            data = response.data
            print(f"   - 差异ID: {data.id}")
            print(f"   - 差异类型: {data.dispute_type}")
            print(f"   - 处理状态: {data.handle_status}")
            print(f"   - 处理备注: {data.handle_remark}")
            print(f"   - 处理人: {data.handler_name}")
            print(f"   - 处理时间: {data.handled_at}")
            
            print(f"\n[TEST 4 PASSED]")
            return True
        except Exception as e:
            print(f"\n[TEST 4 FAILED] {str(e)}")
            import traceback
            traceback.print_exc()
            return False


async def test_5_reconciliation_history():
    """测试5: 历史对账记录"""
    print("\n" + "=" * 60)
    print("[TEST 5] GET /admin/reconciliation/history - 历史对账记录")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        try:
            response = await get_reconciliation_history(
                db=db,
                current_user=MOCK_ADMIN_USER,
                channel=None,
                status=None,
                start_date=None,
                end_date=None,
                page=1,
                page_size=20,
            )
            
            print(f"\n[RESULT]")
            data = response.data
            print(f"   - 总记录数: {data.pagination['total']}")
            print(f"   - 当前页: {data.pagination['page']} / 总页数: {data.pagination['total_pages']}")
            
            if data.items:
                print(f"\n   对账历史:")
                for i, item in enumerate(data.items[:5], 1):
                    print(f"   [{i}] {item.reconcile_date} | {item.channel_name} | 状态: {item.status} | 匹配: {item.match_count} | 长款: {item.long_count} | 短款: {item.short_count}")
            
            print(f"\n[TEST 5 PASSED]")
            return True
        except Exception as e:
            print(f"\n[TEST 5 FAILED] {str(e)}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("RECONCILIATION API TEST SUITE")
    print("=" * 60)
    print(f"Test Time: {datetime.utcnow().isoformat()}")
    
    # 清理旧测试数据
    await cleanup_test_data()
    
    # 准备测试数据
    await setup_test_data()
    
    # 执行测试
    results = {}
    
    # 测试1: 执行对账
    reconciliation_id = await test_1_execute_reconciliation()
    results["执行对账"] = reconciliation_id is not None
    
    # 测试2: 对账结果查询
    if reconciliation_id:
        results["对账结果查询"] = await test_2_get_reconciliation_result(reconciliation_id)
    
    # 测试3: 差异记录列表
    dispute_id = await test_3_get_disputes()
    results["差异记录列表"] = dispute_id is not None
    
    # 测试4: 处理差异
    if dispute_id:
        results["处理差异"] = await test_4_handle_dispute(dispute_id)
    else:
        results["处理差异"] = True  # 无差异时跳过
    
    # 测试5: 历史对账记录
    results["历史对账记录"] = await test_5_reconciliation_history()
    
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
    asyncio.run(main())
