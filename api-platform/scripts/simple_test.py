"""简化的对账API测试"""
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, delete, and_

from src.config.database import AsyncSessionLocal
from src.models import User, Bill, Account, PlatformAccount
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
    
    # Cleanup old data
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.email == 'test_recon@example.com'))
        await db.commit()
    
    # Setup test data
    async with AsyncSessionLocal() as db:
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
        
        bills_data = [
            {'amount': '100.0', 'payment_method': 'alipay', 'status': 'completed'},
            {'amount': '200.0', 'payment_method': 'alipay', 'status': 'completed'},
            {'amount': '50.0', 'payment_method': 'alipay', 'status': 'completed'},
        ]
        for i, bd in enumerate(bills_data):
            bill = Bill(
                user_id=test_user.id, 
                bill_no=f'T_RECON_{i+1}', 
                bill_type='recharge',
                amount=bd['amount'], 
                balance_before='1000.0', 
                balance_after=str(1100.0 + i*200),
                payment_method=bd['payment_method'], 
                status=bd['status'],
                transaction_id=f'TXN_{i+1}', 
                environment='simulation'
            )
            db.add(bill)
        await db.commit()
    
    results = {}
    recon_id = None
    dispute_id = None
    
    # Test 1: Execute reconciliation
    try:
        async with AsyncSessionLocal() as db:
            req = ExecuteReconciliationRequest(
                date=datetime.utcnow().strftime('%Y-%m-%d'), 
                channel='alipay'
            )
            resp = await execute_reconciliation(
                request=req, 
                db=db, 
                current_user=MOCK_ADMIN_USER
            )
            print(f'Test 1 - Execute: PASS (ID={resp.data.reconciliation_id[:8]}...)')
            print(f'  - Platform trades: {resp.data.platform_trade_count}')
            print(f'  - Match count: {resp.data.match_count}')
            print(f'  - Long count: {resp.data.long_count}')
            recon_id = resp.data.reconciliation_id
            results['Execute'] = True
    except Exception as e:
        print(f'Test 1 - Execute: FAIL ({e})')
        results['Execute'] = False
    
    # Test 2: Query result
    try:
        async with AsyncSessionLocal() as db:
            resp = await get_reconciliation_result(
                db=db, 
                current_user=MOCK_ADMIN_USER,
                date=datetime.utcnow().strftime('%Y-%m-%d'), 
                channel='alipay'
            )
            print(f'Test 2 - Query Result: PASS (status={resp.data.status})')
            print(f'  - Match: {resp.data.match_count}, Long: {resp.data.long_count}')
            results['Query Result'] = True
    except Exception as e:
        print(f'Test 2 - Query Result: FAIL ({e})')
        results['Query Result'] = False
    
    # Test 3: List disputes
    try:
        async with AsyncSessionLocal() as db:
            resp = await get_reconciliation_disputes(
                db=db, 
                current_user=MOCK_ADMIN_USER, 
                page=1, 
                page_size=20
            )
            total = resp.data.pagination['total']
            print(f'Test 3 - List Disputes: PASS (total={total})')
            if resp.data.items:
                print(f'  - First dispute type: {resp.data.items[0].dispute_type}')
                dispute_id = resp.data.items[0].id
            results['List Disputes'] = True
    except Exception as e:
        print(f'Test 3 - List Disputes: FAIL ({e})')
        results['List Disputes'] = False
    
    # Test 4: Handle dispute
    try:
        if dispute_id:
            async with AsyncSessionLocal() as db:
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
            print('Test 4 - Handle Dispute: SKIP (no disputes)')
            results['Handle Dispute'] = True
    except Exception as e:
        print(f'Test 4 - Handle Dispute: FAIL ({e})')
        results['Handle Dispute'] = False
    
    # Test 5: History
    try:
        async with AsyncSessionLocal() as db:
            resp = await get_reconciliation_history(
                db=db, 
                current_user=MOCK_ADMIN_USER, 
                page=1, 
                page_size=20
            )
            total = resp.data.pagination['total']
            print(f'Test 5 - History: PASS (total={total})')
            if resp.data.items:
                print(f'  - Latest: {resp.data.items[0].reconcile_date} | {resp.data.items[0].channel_name}')
            results['History'] = True
    except Exception as e:
        print(f'Test 5 - History: FAIL ({e})')
        results['History'] = False
    
    # Cleanup
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.email == 'test_recon@example.com'))
        await db.commit()
    
    print('='*60)
    all_passed = all(results.values())
    print(f'RESULTS: {"ALL PASSED" if all_passed else "SOME FAILED"}')
    for k, v in results.items():
        status = "PASS" if v else "FAIL"
        print(f'  {k}: [{status}]')
    print('='*60)
    
    return all_passed

if __name__ == '__main__':
    asyncio.run(test())
