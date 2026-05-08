#!/usr/bin/env python
"""
数据修复脚本
根据实际数据分析，确定需要修复的记录
"""

import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform"


async def diagnose_and_fix():
    """诊断并修复时区问题"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.execute(text('SET TIME ZONE "UTC"'))
        
        print("=" * 70)
        print("时区问题修复工具")
        print("=" * 70)
        
        # 检查 1.23 元的记录（用户反馈的问题）
        print("\n检查金额 1.23 的充值记录:")
        result = await conn.execute(text("""
            SELECT 
                id,
                bill_no,
                amount,
                created_at,
                created_at AT TIME ZONE 'Asia/Shanghai' as cst_time
            FROM bills
            WHERE bill_type = 'recharge' AND amount = '1.23'
            ORDER BY created_at DESC
        """))
        
        rows = result.fetchall()
        print(f"\n{'ID':<8} {'账单号':<30} {'金额':<8} {'UTC时间':<28} {'中国时间':<28} {'状态':<15}")
        print("-" * 120)
        
        for row in rows:
            bill_id = str(row[0])
            bill_no = str(row[1])[:28]
            amount = str(row[2])
            utc_time = str(row[3])[:26] if row[3] else "N/A"
            cst_time = str(row[4])[:26] if row[4] else "N/A"
            
            # 判断是否需要修复
            # 如果 UTC 时间在 15:00-16:00 之间，而中国时间也在 15:00-16:00
            # 说明数据被当作 UTC 存储了（实际上应该是 UTC+8 的 23:00-24:00）
            if row[3]:
                utc_hour = row[3].hour
                if 14 <= utc_hour <= 16:  # 14:00-16:00 UTC
                    status = "[NEED FIX]"
                else:
                    status = "[OK]"
            else:
                status = "未知"
            
            print(f"{bill_id:<8} {bill_no:<30} {amount:<8} {utc_time:<28} {cst_time:<28} {status:<15}")
        
        # 统计需要修复的记录
        result = await conn.execute(text("""
            SELECT COUNT(*) 
            FROM bills
            WHERE bill_type = 'recharge'
                AND EXTRACT(HOUR FROM created_at) BETWEEN 14 AND 16
        """))
        need_fix_count = result.scalar()
        
        print(f"\n需要修复的记录数: {need_fix_count}")
        
        if need_fix_count > 0:
            print("\n" + "=" * 70)
            print("修复建议")
            print("=" * 70)
            print(f"""
找到 {need_fix_count} 条时区错误的记录。

问题：这些记录的 created_at 被错误地存储为 UTC 时间（15:xx）
实际：它们应该是 UTC+8 时间（23:xx = 15:xx + 8小时）

修复方法：将这些记录的 created_at 加上 8 小时

SQL 语句：
UPDATE bills 
SET created_at = created_at + INTERVAL '8 hours'
WHERE bill_type = 'recharge'
    AND EXTRACT(HOUR FROM created_at) BETWEEN 14 AND 16;

[WARNING] 此操作会修改数据库数据，建议：
1. 先备份数据
2. 确认分析结果正确
3. 确认修复后不会影响其他功能
            """)
        
        # 同时检查 simulation 环境的数据
        print("\n" + "=" * 70)
        print("simulation 环境记录检查")
        print("=" * 70)
        
        result = await conn.execute(text("""
            SELECT COUNT(*) 
            FROM bills
            WHERE bill_type = 'recharge'
                AND environment = 'simulation'
                AND EXTRACT(HOUR FROM created_at) BETWEEN 6 AND 12
        """))
        sim_need_fix = result.scalar()
        
        if sim_need_fix > 0:
            print(f"simulation 环境也有 {sim_need_fix} 条可能需要修复的记录")
        
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(diagnose_and_fix())
