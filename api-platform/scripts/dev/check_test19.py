import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, desc, func
from datetime import datetime, timedelta
import sys
sys.path.insert(0, 'd:/Work_Area/AI/API-Agent/api-platform')
from src.models.billing import Bill

async def test():
    engine = create_async_engine('postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        user_id = "29a6754a-6856-4d59-ab15-5b301ab86447"  # test19@test19.com
        environment = "production"
        
        # 模拟后端查询逻辑
        start_utc = datetime(2026, 5, 7, 16, 0, 0)  # 北京 2026-05-08 00:00
        end_utc = datetime(2026, 5, 8, 15, 59, 59)   # 北京 2026-05-08 23:59
        
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
        
        # 分页查询
        query = select(Bill).where(*base_conditions).order_by(desc(Bill.id)).offset(0).limit(20)
        result = await session.execute(query)
        bills = result.scalars().all()
        
        print(f"API 将返回:")
        print(f"  total: {total}")
        print(f"  items: {len(bills)} 条")
        for bill in bills:
            bj_time = bill.created_at + timedelta(hours=8)
            print(f"    - ID={bill.id}, {bill.bill_type}, {bill.amount}元, 北京时间 {bj_time.strftime('%m-%d %H:%M')}")

asyncio.run(test())
