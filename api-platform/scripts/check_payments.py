#!/usr/bin/env python
"""检查 payments 表结构"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def check():
    engine = create_async_engine('postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform', echo=False)
    async with engine.begin() as conn:
        await conn.execute(text('SET TIME ZONE "UTC"'))
        
        # 检查 payments 表结构
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'payments'
            ORDER BY ordinal_position
        """))
        print('payments 表结构:')
        for row in result.fetchall():
            print(f'  {row[0]}: {row[1]}')
        
        print('\n检查 payments 和 bills 时间对比:')
        result = await conn.execute(text("""
            SELECT 
                b.id as bill_id,
                b.bill_no,
                b.amount,
                b.created_at as bill_created_at,
                p.id as payment_id,
                p.created_at as payment_created_at,
                EXTRACT(EPOCH FROM (p.created_at - b.created_at)) as time_diff_seconds
            FROM bills b
            LEFT JOIN payments p ON p.transaction_id = b.transaction_id
            WHERE b.bill_type = 'recharge' 
                AND b.transaction_id IS NOT NULL
                AND p.id IS NOT NULL
            ORDER BY b.created_at DESC
            LIMIT 20
        """))
        
        rows = result.fetchall()
        print(f"\n{'账单ID':<8} {'金额':<8} {'账单创建时间(UTC)':<30} {'支付创建时间(UTC)':<30} {'差异(秒)':<10}")
        print("-" * 100)
        
        for row in rows:
            bill_id = str(row[0])[:8]
            amount = row[2]
            bill_time = row[3]
            payment_time = row[5]
            diff = row[6]
            
            bill_str = str(bill_time)[:26] if bill_time else "N/A"
            payment_str = str(payment_time)[:26] if payment_time else "N/A"
            diff_str = f"{diff:.0f}s" if diff else "N/A"
            
            # 标记异常差异（约8小时 = 28800秒）
            flag = " ⚠️" if diff and abs(diff) > 27000 and abs(diff) < 30000 else ""
            
            print(f"{bill_id:<8} {amount:<8} {bill_str:<30} {payment_str:<30} {diff_str:<10}{flag}")
        
        # 统计问题记录
        result = await conn.execute(text("""
            SELECT COUNT(*) 
            FROM bills b
            JOIN payments p ON p.transaction_id = b.transaction_id
            WHERE b.bill_type = 'recharge' 
                AND b.transaction_id IS NOT NULL
                AND p.id IS NOT NULL
                AND EXTRACT(EPOCH FROM (p.created_at - b.created_at)) BETWEEN 27000 AND 30000
        """))
        count = result.scalar()
        print(f"\n存在 8 小时差异的记录数: {count}")
        
    await engine.dispose()

asyncio.run(check())
