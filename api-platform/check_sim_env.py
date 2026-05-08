import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from datetime import datetime, timedelta

async def test():
    engine = create_async_engine('postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # simulation 环境 5月8日
        result = await session.execute(text('''
            SELECT user_id, COUNT(*) as count
            FROM bills 
            WHERE created_at >= '2026-05-07 16:00:00' 
              AND created_at <= '2026-05-08 15:59:59'
              AND environment = 'simulation'
            GROUP BY user_id
        '''))
        
        print('=== simulation 环境 5月8日账单 ===')
        rows = result.fetchall()
        print(f'总用户数: {len(rows)}')
        total = sum(r[1] for r in rows)
        print(f'总记录数: {total}')
        for r in rows:
            print(f'  user_id={r[0]}, count={r[1]}')
        
        # 查看 simulation 环境 5月9日的记录
        result2 = await session.execute(text('''
            SELECT user_id, COUNT(*) as count
            FROM bills 
            WHERE created_at >= '2026-05-08 16:00:00' 
              AND created_at <= '2026-05-09 15:59:59'
              AND environment = 'simulation'
            GROUP BY user_id
        '''))
        
        print('\n=== simulation 环境 5月9日账单 ===')
        rows2 = result2.fetchall()
        print(f'总用户数: {len(rows2)}')
        total2 = sum(r[1] for r in rows2)
        print(f'总记录数: {total2}')

asyncio.run(test())
