#!/usr/bin/env python
"""
数据库时区检查脚本
用于验证时区设置和时间数据存储情况
"""

import asyncio
import sys
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Database connection
DATABASE_URL = "postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform"


async def check_timezone():
    """检查数据库时区和时间数据"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        print("=" * 60)
        print("1. 检查数据库会话时区设置")
        print("=" * 60)
        
        # 检查当前会话时区
        result = await conn.execute(text("SHOW TIME ZONE"))
        session_tz = result.scalar()
        print(f"当前会话时区: {session_tz}")
        
        # 设置 UTC 时区
        await conn.execute(text("SET TIME ZONE 'UTC'"))
        result = await conn.execute(text("SHOW TIME ZONE"))
        new_tz = result.scalar()
        print(f"设置后的会话时区: {new_tz}")
        
        print("\n" + "=" * 60)
        print("2. 检查 bills 表时间数据")
        print("=" * 60)
        
        # 检查 bills 表的时间数据
        result = await conn.execute(text("""
            SELECT 
                id,
                bill_type,
                amount,
                created_at,
                created_at AT TIME ZONE 'UTC' as created_at_utc,
                created_at AT TIME ZONE 'Asia/Shanghai' as created_at_cst,
                NOW() as now_utc,
                NOW() AT TIME ZONE 'Asia/Shanghai' as now_cst
            FROM bills 
            ORDER BY created_at DESC 
            LIMIT 10
        """))
        
        rows = result.fetchall()
        if rows:
            print(f"\n最近 10 条账单记录：")
            print(f"{'ID':<10} {'类型':<12} {'金额':<10} {'原始存储':<30} {'UTC':<30} {'中国时间':<30}")
            print("-" * 130)
            for row in rows:
                original = str(row[3]) if row[3] else "None"
                utc = str(row[4]) if row[4] else "None"
                cst = str(row[5]) if row[5] else "None"
                print(f"{str(row[0]):<10} {str(row[1]):<12} {str(row[2]):<10} {original:<30} {utc:<30} {cst:<30}")
        else:
            print("bills 表没有数据")
        
        print("\n" + "=" * 60)
        print("3. 检查 payments 表时间数据")
        print("=" * 60)
        
        result = await conn.execute(text("""
            SELECT 
                id,
                payment_no,
                status,
                amount,
                created_at,
                created_at AT TIME ZONE 'UTC' as created_at_utc,
                created_at AT TIME ZONE 'Asia/Shanghai' as created_at_cst,
                pay_time
            FROM payments 
            ORDER BY created_at DESC 
            LIMIT 10
        """))
        
        rows = result.fetchall()
        if rows:
            print(f"\n最近 10 条支付记录：")
            print(f"{'ID':<10} {'支付号':<20} {'状态':<12} {'金额':<10} {'原始存储':<30} {'UTC':<30} {'中国时间':<30}")
            print("-" * 150)
            for row in rows:
                original = str(row[4]) if row[4] else "None"
                utc = str(row[5]) if row[5] else "None"
                cst = str(row[6]) if row[6] else "None"
                print(f"{str(row[0]):<10} {str(row[1]):<20} {str(row[2]):<12} {str(row[3]):<10} {original:<30} {utc:<30} {cst:<30}")
        else:
            print("payments 表没有数据")
        
        print("\n" + "=" * 60)
        print("4. 检查 users 表时间数据（作为对比）")
        print("=" * 60)
        
        result = await conn.execute(text("""
            SELECT 
                id,
                email,
                created_at,
                created_at AT TIME ZONE 'UTC' as created_at_utc,
                created_at AT TIME ZONE 'Asia/Shanghai' as created_at_cst
            FROM users 
            ORDER BY created_at DESC 
            LIMIT 5
        """))
        
        rows = result.fetchall()
        if rows:
            print(f"\n最近 5 个用户：")
            print(f"{'ID':<40} {'邮箱':<40} {'原始存储':<30} {'UTC':<30} {'中国时间':<30}")
            print("-" * 170)
            for row in rows:
                original = str(row[2]) if row[2] else "None"
                utc = str(row[3]) if row[3] else "None"
                cst = str(row[4]) if row[4] else "None"
                print(f"{str(row[0]):<40} {str(row[1]):<40} {original:<30} {utc:<30} {cst:<30}")
        else:
            print("users 表没有数据")
        
        print("\n" + "=" * 60)
        print("5. 时间字段分析总结")
        print("=" * 60)
        
        # 分析 bills 表的时间分布
        result = await conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                MIN(created_at) as earliest,
                MAX(created_at) as latest
            FROM bills
        """))
        row = result.fetchone()
        if row and row[0] > 0:
            print(f"bills 表: 共 {row[0]} 条记录")
            print(f"  最早记录: {row[1]}")
            print(f"  最新记录: {row[2]}")
        
        print("\n" + "=" * 60)
        print("6. 建议")
        print("=" * 60)
        print("""
如果原始存储的时间 + 8小时 = 中国时间，说明数据库存储的是 UTC 时间。
如果原始存储的时间 = 中国时间，说明数据库存储的是本地时间。

根据分析结果决定是否需要数据迁移。
        """)
    
    await engine.dispose()


async def check_api_responses():
    """模拟 API 响应检查时区转换逻辑"""
    print("\n" + "=" * 60)
    print("7. 模拟 _to_utc_iso_string 函数")
    print("=" * 60)
    
    def _to_utc_iso_string(dt):
        """模拟 Python 端的转换逻辑"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            # 假设 naive datetime 是 UTC+8
            local_tz = timezone(timedelta(hours=8))
            dt = dt.replace(tzinfo=local_tz)
        return dt.astimezone(timezone.utc).isoformat()
    
    # 测试用例
    test_cases = [
        datetime(2026, 5, 8, 23, 45, 0),  # naive, 假设是本地时间
        datetime(2026, 5, 8, 23, 45, 0, tzinfo=timezone.utc),  # UTC aware
        datetime(2026, 5, 8, 15, 45, 0, tzinfo=timezone(timedelta(hours=8))),  # UTC+8 aware
    ]
    
    print("\n测试场景 1: naive datetime (2026-05-08 23:45:00)")
    print("  期望: 前端显示 2026-05-09 07:45 (UTC+0)")
    print(f"  实际: {_to_utc_iso_string(test_cases[0])}")
    
    print("\n测试场景 2: UTC aware (2026-05-08 23:45:00+00:00)")
    print("  期望: 前端显示 2026-05-09 07:45 (UTC+0)")
    print(f"  实际: {_to_utc_iso_string(test_cases[1])}")
    
    print("\n测试场景 3: UTC+8 aware (2026-05-08 23:45:00+08:00)")
    print("  期望: 前端显示 2026-05-09 07:45 (UTC+0)")
    print(f"  实际: {_to_utc_iso_string(test_cases[2])}")


if __name__ == "__main__":
    print("数据库时区检查工具")
    print("=" * 60)
    asyncio.run(check_timezone())
    asyncio.run(check_api_responses())
