import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def test():
    engine = create_async_engine('postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 查看数据库时区设置
        result = await session.execute(text('SHOW timezone'))
        db_tz = result.scalar()
        print(f"数据库时区设置: {db_tz}")
        
        # 查看一条记录的实际存储值
        result2 = await session.execute(text('''
            SELECT id, amount, created_at, created_at AT TIME ZONE 'Asia/Shanghai' as beijing_time
            FROM bills 
            WHERE id = 212
        '''))
        row = result2.fetchone()
        print(f"\nID=212 的时间:")
        print(f"  存储值 (UTC): {row[2]}")
        print(f"  北京时间: {row[3]}")
        
        # 直接查询，不用 AT TIME ZONE
        result3 = await session.execute(text('''
            SELECT id, created_at, created_at::text
            FROM bills 
            WHERE id = 212
        '''))
        row3 = result3.fetchone()
        print(f"\n原始存储值: {row3[2]}")

asyncio.run(test())
