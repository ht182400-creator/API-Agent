#!/usr/bin/env python
"""详细检查 bills 和 payments 表"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def check():
    engine = create_async_engine('postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform', echo=False)
    async with engine.begin() as conn:
        await conn.execute(text('SET TIME ZONE "UTC"'))
        
        # 检查 bills 表结构
        print("bills 表结构:")
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'bills'
            ORDER BY ordinal_position
        """))
        for row in result.fetchall():
            print(f'  {row[0]}: {row[1]}')
        
        # 查看最近几笔充值的详情
        print("\n\n最近 10 笔充值账单详情:")
        result = await conn.execute(text("""
            SELECT 
                b.id,
                b.bill_no,
                b.bill_type,
                b.amount,
                b.transaction_id,
                b.description,
                b.created_at,
                b.created_at AT TIME ZONE 'UTC' as as_utc,
                b.created_at AT TIME ZONE 'Asia/Shanghai' as as_cst
            FROM bills b
            WHERE b.bill_type = 'recharge'
            ORDER BY b.created_at DESC
            LIMIT 10
        """))
        
        print(f"\n{'ID':<6} {'账单号':<25} {'金额':<8} {'transaction_id':<40} {'原始存储':<28} {'UTC':<28} {'中国时间':<28}")
        print("-" * 170)
        
        for row in result.fetchall():
            bill_id = str(row[0])
            bill_no = str(row[1])[:24]
            amount = str(row[3])
            txn_id = str(row[4])[:38] if row[4] else "NULL"
            original = str(row[6])[:26] if row[6] else "N/A"
            as_utc = str(row[7])[:26] if row[7] else "N/A"
            as_cst = str(row[8])[:26] if row[8] else "N/A"
            
            print(f"{bill_id:<6} {bill_no:<25} {amount:<8} {txn_id:<40} {original:<28} {as_utc:<28} {as_cst:<28}")
        
        # 检查同一笔充值在 payments 表的时间
        print("\n\n检查关联的 payments 记录:")
        result = await conn.execute(text("""
            SELECT 
                b.bill_no,
                b.transaction_id,
                p.payment_no,
                b.created_at as bill_created,
                p.created_at as payment_created,
                EXTRACT(EPOCH FROM (p.created_at - b.created_at)) as diff
            FROM bills b
            INNER JOIN payments p ON p.payment_no = b.transaction_id
            WHERE b.bill_type = 'recharge' AND b.transaction_id IS NOT NULL
            ORDER BY b.created_at DESC
            LIMIT 10
        """))
        
        rows = result.fetchall()
        if rows:
            print(f"\n{'账单号':<25} {'payment_no':<25} {'账单时间':<28} {'支付时间':<28} {'差异':<12}")
            print("-" * 120)
            for row in rows:
                bill_no = str(row[0])[:24]
                payment_no = str(row[2])[:24]
                bill_time = str(row[3])[:26] if row[3] else "N/A"
                payment_time = str(row[4])[:26] if row[4] else "N/A"
                diff = f"{row[5]:.0f}s" if row[5] else "N/A"
                flag = " ⚠️" if row[5] and abs(row[5]) > 27000 and abs(row[5]) < 30000 else ""
                print(f"{bill_no:<25} {payment_no:<25} {bill_time:<28} {payment_time:<28} {diff:<12}{flag}")
        else:
            print("没有找到关联的 payments 记录")
            
        # 直接查看 payments 表的时间
        print("\n\npayments 表最近 5 条记录:")
        result = await conn.execute(text("""
            SELECT 
                payment_no,
                status,
                amount,
                created_at,
                created_at AT TIME ZONE 'UTC' as as_utc,
                created_at AT TIME ZONE 'Asia/Shanghai' as as_cst
            FROM payments
            ORDER BY created_at DESC
            LIMIT 5
        """))
        
        print(f"\n{'payment_no':<25} {'状态':<12} {'金额':<8} {'原始':<28} {'UTC':<28} {'中国时间':<28}")
        print("-" * 120)
        for row in result.fetchall():
            payment_no = str(row[0])[:24]
            status = str(row[1])
            amount = str(row[2])
            original = str(row[3])[:26] if row[3] else "N/A"
            as_utc = str(row[4])[:26] if row[4] else "N/A"
            as_cst = str(row[5])[:26] if row[5] else "N/A"
            print(f"{payment_no:<25} {status:<12} {amount:<8} {original:<28} {as_utc:<28} {as_cst:<28}")
    
    await engine.dispose()

asyncio.run(check())
