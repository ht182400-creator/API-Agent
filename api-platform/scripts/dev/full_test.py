import asyncio
from datetime import datetime, timezone, timedelta
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
    
    # 前端传的日期
    start_date = "2026-05-08"
    end_date = "2026-05-08"
    
    # 后端转换逻辑
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    start_utc = start_dt - timedelta(hours=8)
    
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    end_utc = end_dt - timedelta(hours=8)
    
    print(f"前端传: start_date={start_date}, end_date={end_date}")
    print(f"后端转换: start_utc={start_utc}, end_utc={end_utc}")
    
    async with async_session() as session:
        base_conditions = [
            Bill.user_id == user_id,
            Bill.environment == environment,
            Bill.created_at >= start_utc,
            Bill.created_at <= end_utc,
        ]
        
        # 模拟 API 返回格式
        count_query = select(func.count(Bill.id)).where(*base_conditions)
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = select(Bill).where(*base_conditions).order_by(desc(Bill.id)).offset(0).limit(20)
        result = await session.execute(query)
        bills = result.scalars().all()
        
        print(f"\n=== API 会返回 ===")
        print(f'total: {total}, items: {len(bills)} 条')
        for bill in bills:
            # 模拟 _to_utc_iso_string
            if bill.created_at.tzinfo is None:
                utc_dt = bill.created_at.replace(tzinfo=timezone.utc)
            else:
                utc_dt = bill.created_at.astimezone(timezone.utc)
            utc_str = utc_dt.isoformat()
            print(f'  ID={bill.id}, amount={bill.amount}, created_at="{utc_str}"')
        
        print(f"\n=== 如果前端 dayjs 解析 ===")
        # dayjs 在中国浏览器会解析为北京时间
        for bill in bills:
            utc_dt = bill.created_at.replace(tzinfo=timezone.utc) if bill.created_at.tzinfo is None else bill.created_at.astimezone(timezone.utc)
            # 模拟 dayjs 转为本地时间（UTC+8）
            local_dt = utc_dt.astimezone()  # 转为本地时区
            display = local_dt.strftime('%Y-%m-%d %H:%M:%S')
            print(f"  {bill.id}: {display}")

asyncio.run(test())
