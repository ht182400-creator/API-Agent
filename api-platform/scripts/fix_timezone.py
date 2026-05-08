#!/usr/bin/env python
"""
数据库时区数据修复脚本
检查并修复历史数据的时区问题
"""

import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform"


async def analyze_timezone_issue():
    """分析时区问题"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        # 设置 UTC 时区
        await conn.execute(text("SET TIME ZONE 'UTC'"))
        
        print("=" * 70)
        print("时区问题分析")
        print("=" * 70)
        
        # 检查 bills 和 payments 的时间差异
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
                AND p.environment = b.environment
            WHERE b.bill_type = 'recharge' 
                AND b.transaction_id IS NOT NULL
            ORDER BY b.created_at DESC
            LIMIT 20
        """))
        
        rows = result.fetchall()
        print("\n账单与支付记录的时间对比（充值订单）：")
        print(f"{'账单ID':<8} {'金额':<8} {'账单创建时间':<30} {'支付创建时间':<30} {'差异(秒)':<10}")
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
        
        print("\n" + "=" * 70)
        print("问题诊断")
        print("=" * 70)
        
        # 检查是否有 8 小时差异的记录
        result = await conn.execute(text("""
            SELECT COUNT(*) 
            FROM bills b
            JOIN payments p ON p.transaction_id = b.transaction_id 
            WHERE b.bill_type = 'recharge' 
                AND b.transaction_id IS NOT NULL
                AND EXTRACT(EPOCH FROM (p.created_at - b.created_at)) BETWEEN 27000 AND 30000
        """))
        count = result.scalar()
        
        if count > 0:
            print(f"\n发现 {count} 条记录存在约 8 小时的时间差异！")
            print("原因分析：")
            print("  - bills 表和 payments 表在同一时间创建，但显示时间不同")
            print("  - 可能是写入时数据库会话时区不一致导致的")
            print("\n影响：")
            print("  - 前端显示的账单时间比实际时间早 8 小时")
            print("\n修复方案：")
            print("  1. 新数据：已通过设置 SET TIME ZONE 'UTC' 修复")
            print("  2. 历史数据：需要将 bills.created_at 加上 8 小时")
        else:
            print("\n没有发现明显的 8 小时差异问题")
        
        print("\n" + "=" * 70)
        print("数据修复建议")
        print("=" * 70)
        print("""
方案 A: 不修改数据库，通过 API 层修复
  - 在 _to_utc_iso_string 函数中添加检测逻辑
  - 如果发现时间异常（比其他关联记录早 8 小时），自动校正

方案 B: 直接修改数据库
  - UPDATE bills SET created_at = created_at + INTERVAL '8 hours'
  - WHERE bill_type = 'recharge' 
    AND EXISTS (SELECT 1 FROM payments WHERE transaction_id = bills.transaction_id)
  - 风险：会永久修改数据，如果分析错误会导致数据损坏

推荐：先使用方案 A，确认无误后再考虑方案 B
        """)
    
    await engine.dispose()


async def fix_via_api_layer():
    """
    方案 A: 通过 API 层修复
    检测 bills.created_at 是否比关联的 payments.created_at 早约 8 小时
    如果是，说明数据有问题，返回校正后的时间
    """
    print("\n" + "=" * 70)
    print("方案 A: API 层修复逻辑")
    print("=" * 70)
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.execute(text("SET TIME ZONE 'UTC'"))
        
        # 检查需要修复的记录
        result = await conn.execute(text("""
            SELECT 
                b.id,
                b.bill_no,
                b.created_at,
                p.created_at as payment_created_at,
                EXTRACT(EPOCH FROM (p.created_at - b.created_at)) as diff
            FROM bills b
            JOIN payments p ON p.transaction_id = b.transaction_id 
            WHERE b.bill_type = 'recharge' 
                AND b.transaction_id IS NOT NULL
                AND p.created_at IS NOT NULL
                AND EXTRACT(EPOCH FROM (p.created_at - b.created_at)) BETWEEN 27000 AND 30000
        """))
        
        rows = result.fetchall()
        
        if not rows:
            print("没有需要修复的记录")
            await engine.dispose()
            return
        
        print(f"\n发现 {len(rows)} 条需要修复的记录：")
        print(f"{'ID':<8} {'账单号':<25} {'原始时间':<30} {'支付时间':<30} {'校正后时间':<30}")
        print("-" * 125)
        
        for row in rows:
            bill_id = str(row[0])
            bill_no = row[1]
            bill_created = row[2]
            payment_created = row[3]
            diff = row[4]
            
            # 原始时间
            original_str = str(bill_created)[:26] if bill_created else "N/A"
            # 支付时间
            payment_str = str(payment_created)[:26] if payment_created else "N/A"
            # 校正后时间 = 原始时间 + 8 小时
            if bill_created:
                fixed = bill_created + timedelta(hours=8)
                fixed_str = str(fixed)[:26]
            else:
                fixed_str = "N/A"
            
            print(f"{bill_id[:8]:<8} {bill_no[:25]:<25} {original_str:<30} {payment_str:<30} {fixed_str:<30}")
        
        print(f"\n共 {len(rows)} 条记录需要修复")
        print("\n修复方法：在 _to_utc_iso_string 函数中添加检测逻辑")
    
    await engine.dispose()


if __name__ == "__main__":
    print("数据库时区问题诊断与修复工具")
    print("=" * 70)
    asyncio.run(analyze_timezone_issue())
    asyncio.run(fix_via_api_layer())
