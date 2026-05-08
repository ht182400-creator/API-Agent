import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, desc, func
import sys
sys.path.insert(0, 'd:/Work_Area/AI/API-Agent/api-platform')

from src.models.billing import Bill

async def test():
    engine = create_async_engine('postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    user_id = "29a6754a-6856-4d59-ab15-5b301ab86447"  # test19
    environment = "production"
    
    # 模拟后端逻辑
    start_date = "2026-05-08"
    end_date = "2026-05-08"
    
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    start_utc = start_dt - timedelta(hours=8)  # 2026-05-07 16:00:00
    
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    end_utc = end_dt - timedelta(hours=8)  # 2026-05-08 15:59:59
    
    print(f"筛选范围: UTC {start_utc} 到 {end_utc}")
    
    async with async_session() as session:
        base_conditions = [
            Bill.user_id == user_id,
            Bill.environment == environment,
            Bill.created_at >= start_utc,
            Bill.created_at <= end_utc,
        ]
        
        # 计数
        count_query = select(func.count(Bill.id)).where(*base_conditions)
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        print(f"\n数据库查询结果: total={total}")
        
        # 分页查询
        query = select(Bill).where(*base_conditions).order_by(desc(Bill.id)).offset(0).limit(20)
        result = await session.execute(query)
        bills = result.scalars().all()
        print(f"返回记录数: {len(bills)}")
        
        for bill in bills:
            bj_time = bill.created_at + timedelta(hours=8)
            print(f"  ID={bill.id}, amount={bill.amount}, UTC={bill.created_at}, 北京={bj_time}")

asyncio.run(test())
