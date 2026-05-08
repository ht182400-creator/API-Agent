import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from datetime import datetime, timedelta

async def test():
    engine = create_async_engine('postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 检查 5月8日有账单的用户 ID 是否在 users 表中
        result = await session.execute(text('''
            SELECT DISTINCT b.user_id, u.email 
            FROM bills b
            LEFT JOIN users u ON b.user_id = u.id
            WHERE b.created_at >= '2026-05-07 16:00:00' 
              AND b.created_at <= '2026-05-08 15:59:59'
              AND b.environment = 'production'
        '''))
        
        print('=== 5月8日账单的用户 ===')
        for r in result.fetchall():
            print(f'  user_id={r[0]}, email={r[1]}')
        
        # 检查 production 环境总数
        result2 = await session.execute(text('''
            SELECT COUNT(*) FROM bills WHERE environment = 'production'
        '''))
        print(f'\nproduction 环境总账单数: {result2.scalar()}')
        
        # 检查 simulation 环境总数
        result3 = await session.execute(text('''
            SELECT COUNT(*) FROM bills WHERE environment = 'simulation'
        '''))
        print(f'simulation 环境总账单数: {result3.scalar()}')

asyncio.run(test())
