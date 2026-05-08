#!/usr/bin/env python
"""检查 bills 表的 description 字段"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def check():
    engine = create_async_engine('postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform', echo=False)
    async with engine.begin() as conn:
        await conn.execute(text('SET TIME ZONE "UTC"'))
        
        print("检查 bills 表 description 字段（可能存储 payment_no）:")
        result = await conn.execute(text("""
            SELECT 
                id,
                bill_no,
                bill_type,
                amount,
                description,
                transaction_id,
                environment,
                created_at
            FROM bills
            WHERE bill_type = 'recharge'
            ORDER BY created_at DESC
            LIMIT 20
        """))
        
        print(f"{'ID':<6} {'金额':<8} {'transaction_id':<10} {'env':<12} {'description':<50} {'created_at':<28}")
        print("-" * 130)
        
        for row in result.fetchall():
            bill_id = str(row[0])
            amount = str(row[3])
            txn_id = str(row[5])[:8] if row[5] else "NULL"
            env = str(row[6])
            desc = str(row[4])[:48] if row[4] else "NULL"
            created = str(row[7])[:26] if row[7] else "N/A"
            print(f"{bill_id:<6} {amount:<8} {txn_id:<10} {env:<12} {desc:<50} {created:<28}")
        
        print("\n\n按 environment 分组统计:")
        result = await conn.execute(text("""
            SELECT environment, COUNT(*), MIN(created_at), MAX(created_at)
            FROM bills
            WHERE bill_type = 'recharge'
            GROUP BY environment
            ORDER BY MAX(created_at) DESC
        """))
        
        print(f"{'environment':<15} {'数量':<10} {'最早':<28} {'最晚':<28}")
        print("-" * 90)
        for row in result.fetchall():
            env = str(row[0]) if row[0] else "NULL"
            count = str(row[1])
            min_time = str(row[2])[:26] if row[2] else "N/A"
            max_time = str(row[3])[:26] if row[3] else "N/A"
            print(f"{env:<15} {count:<10} {min_time:<28} {max_time:<28}")
        
        # 检查同一环境下，时间异常的记录
        print("\n\n检查 simulation 环境的账单时间分布:")
        result = await conn.execute(text("""
            SELECT 
                created_at,
                created_at AT TIME ZONE 'UTC' as utc_time,
                created_at AT TIME ZONE 'Asia/Shanghai' as cst_time
            FROM bills
            WHERE bill_type = 'recharge' AND environment = 'simulation'
            ORDER BY created_at DESC
            LIMIT 20
        """))
        
        print(f"{'原始存储':<28} {'UTC':<28} {'中国时间':<28}")
        print("-" * 85)
        for row in result.fetchall():
            original = str(row[0])[:26] if row[0] else "N/A"
            utc = str(row[1])[:26] if row[1] else "N/A"
            cst = str(row[2])[:26] if row[2] else "N/A"
            print(f"{original:<28} {utc:<28} {cst:<28}")
    
    await engine.dispose()

asyncio.run(check())
