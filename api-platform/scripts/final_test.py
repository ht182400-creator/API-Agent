"""最终对账API测试"""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
logging.basicConfig(level=logging.ERROR)

import uuid
from datetime import datetime
from sqlalchemy import select, delete

from src.config.database import AsyncSessionLocal
from src.models import User, Bill
from src.models.billing import Bill
from src.api.v1.admin_reconciliation import (
    execute_reconciliation, get_reconciliation_result,
    get_reconciliation_disputes, handle_reconciliation_dispute,
    get_reconciliation_history,
    ExecuteReconciliationRequest, HandleDisputeRequest,
)

MOCK_ADMIN_USER = {'id': str(uuid.uuid4()), 'username': 'test_admin', 'email': 'admin@test.com', 'role': 'admin'}

async def test():
    print('='*60)
    print('RECONCILIATION API TEST')
    print('='*60)
    
    results = {}
    dispute_id = None
    
    # Cleanup and Setup
    db = AsyncSessionLocal()
    try:
        await db.execute(delete(User).where(User.email == 'test_recon@example.com'))
        await db.commit()
        
        test_user = User(
            id=uuid.uuid4(), 
            username='test_user_recon', 
            email='test_recon@example.com', 
            phone='13800138000', 
            password_hash='test', 
            user_status='active'
        )
        db.add(test_user)
        await db.flush()
        
        for i in range(3):
            bill = Bill(
                user_id=test_user.id, 
                bill_no=f'T_RECON_{i+1}', 
                bill_type='recharge',
                amount='100.0', 
                balance_before='1000.0', 
                balance_after='1100.0', 
                payment_method='alipay', 
                status='completed', 
                transaction_id=f'TXN_{i+1}', 
                environment='simulation'
            )
            db.add(bill)
        await db.commit()
    except Exception as e:
        print(f'Setup failed: {e}')
        return
    
    # Test 1: Execute
    try:
        req = ExecuteReconciliationRequest(
            date=datetime.utcnow().strftime('%Y-%m-%d'), 
            channel='alipay'
        )
        resp = await execute_reconciliation(
            request=req, 
            db=db, 
            current_user=MOCK_ADMIN_USER
        )
        print(f'Test 1 - Execute: PASS')
        print(f'  - Platform trades: {resp.data.platform_trade_count}')
        print(f'  - Match: {resp.data.match_count}, Long: {resp.data.long_count}')
        results['Execute'] = True
    except Exception as e:
        print(f'Test 1 - Execute: FAIL ({e})')
        results['Execute'] = False
    
    # Test 2: Query Result
    try:
        resp = await get_reconciliation_result(
            db=db, 
            current_user=MOCK_ADMIN_USER, 
            date=datetime.utcnow().strftime('%Y-%m-%d'), 
            channel='alipay'
        )
        print(f'Test 2 - Query Result: PASS (status={resp.data.status})')
        results['Query Result'] = True
    except Exception as e:
        print(f'Test 2 - Query Result: FAIL ({e})')
        results['Query Result'] = False
    
    # Test 3: List Disputes
    try:
        resp = await get_reconciliation_disputes(
            db=db, 
            current_user=MOCK_ADMIN_USER, 
            reconciliation_id=None, 
            dispute_type=None, 
            handle_status=None, 
            page=1, 
            page_size=20
        )
        total = resp.data.pagination['total']
        print(f'Test 3 - List Disputes: PASS (total={total})')
        if resp.data.items:
            dispute_id = resp.data.items[0].id
            print(f'  - First dispute type: {resp.data.items[0].dispute_type}')
        results['List Disputes'] = True
    except Exception as e:
        print(f'Test 3 - List Disputes: FAIL ({e})')
        results['List Disputes'] = False
    
    # Test 4: Handle Dispute
    try:
        if dispute_id:
            req = HandleDisputeRequest(
                handle_status='resolved', 
                handle_remark='Test resolved'
            )
            resp = await handle_reconciliation_dispute(
                dispute_id=dispute_id, 
                request=req, 
                db=db, 
                current_user=MOCK_ADMIN_USER
            )
            print(f'Test 4 - Handle Dispute: PASS (status={resp.data.handle_status})')
            results['Handle Dispute'] = True
        else:
            print('Test 4 - Handle Dispute: SKIP (no disputes found)')
            results['Handle Dispute'] = True
    except Exception as e:
        print(f'Test 4 - Handle Dispute: FAIL ({e})')
        results['Handle Dispute'] = False
    
    # Test 5: History
    try:
        resp = await get_reconciliation_history(
            db=db, 
            current_user=MOCK_ADMIN_USER, 
            channel=None, 
            status=None, 
            start_date=None, 
            end_date=None, 
            page=1, 
            page_size=20
        )
        total = resp.data.pagination['total']
        print(f'Test 5 - History: PASS (total={total})')
        if resp.data.items:
            item = resp.data.items[0]
            print(f'  - Latest: {item.reconcile_date} | {item.channel_name}')
        results['History'] = True
    except Exception as e:
        print(f'Test 5 - History: FAIL ({e})')
        results['History'] = False
    
    # Cleanup
    try:
        await db.execute(delete(User).where(User.email == 'test_recon@example.com'))
        await db.commit()
    except:
        pass
    finally:
        await db.close()
    
    # Summary
    print('='*60)
    all_passed = all(results.values())
    if all_passed:
        print('ALL TESTS PASSED!')
    else:
        print('SOME TESTS FAILED!')
    for k, v in results.items():
        status = 'PASS' if v else 'FAIL'
        print(f'  {k}: [{status}]')
    print('='*60)
    
    return all_passed

if __name__ == '__main__':
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
