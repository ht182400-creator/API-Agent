"""调试对账API测试"""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# 禁用SQL日志
logging.basicConfig(level=logging.ERROR)

import uuid
from datetime import datetime
from sqlalchemy import select, delete, and_

from src.config.database import AsyncSessionLocal
from src.models import User, Bill
from src.models.billing import Bill
from src.api.v1.admin_reconciliation import (
    ExecuteReconciliationRequest,
)

MOCK_ADMIN_USER = {'id': str(uuid.uuid4()), 'username': 'test_admin', 'email': 'admin@test.com', 'role': 'admin'}

async def test():
    print('='*60)
    print('Debug: Test get_reconciliation_disputes')
    print('='*60)
    
    # Cleanup
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.email == 'test_recon@example.com'))
        await db.commit()
    
    # Setup data
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
        
        # Create bills
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
    
    # Test 1: Execute
    print('\n[1] Testing execute_reconciliation...')
    from src.api.v1.admin_reconciliation import execute_reconciliation
    
    async with AsyncSessionLocal() as db:
        req = ExecuteReconciliationRequest(
            date=datetime.utcnow().strftime('%Y-%m-%d'), 
            channel='alipay'
        )
        resp = await execute_reconciliation(request=req, db=db, current_user=MOCK_ADMIN_USER)
        print(f'  Result: ID={resp.data.reconciliation_id[:8]}...')
        print(f'  Platform trades: {resp.data.platform_trade_count}')
        print(f'  Match: {resp.data.match_count}, Long: {resp.data.long_count}')
    
    # Test 2: List disputes - using the API function directly
    print('\n[2] Testing get_reconciliation_disputes directly...')
    from src.api.v1.admin_reconciliation import get_reconciliation_disputes
    
    # Check function signature
    import inspect
    sig = inspect.signature(get_reconciliation_disputes)
    print(f'  Function params: {list(sig.parameters.keys())}')
    
    async with AsyncSessionLocal() as db:
        try:
            # Call with minimal params
            resp = await get_reconciliation_disputes(
                db=db,
                current_user=MOCK_ADMIN_USER,
                reconciliation_id=None,
                dispute_type=None,
                handle_status=None,
                page=1,
                page_size=20
            )
            print(f'  Result: total={resp.data.pagination["total"]}')
        except Exception as e:
            print(f'  Error: {type(e).__name__}: {e}')
            import traceback
            traceback.print_exc()
    
    # Cleanup
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.email == 'test_recon@example.com'))
        await db.commit()

if __name__ == '__main__':
    asyncio.run(test())
