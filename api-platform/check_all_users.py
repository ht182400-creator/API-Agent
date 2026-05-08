import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def test():
    engine = create_async_engine('postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 查看 production 环境 5月8日每个用户的记录数
        result = await session.execute(text('''
            SELECT user_id, COUNT(*) as count, u.email
            FROM bills b
            LEFT JOIN users u ON b.user_id = u.id
            WHERE b.created_at >= '2026-05-07 16:00:00' 
              AND b.created_at <= '2026-05-08 15:59:59'
              AND b.environment = 'production'
            GROUP BY user_id, u.email
            ORDER BY count DESC
        '''))
        
        print('=== production 环境 5月8日所有用户的账单数 ===')
        rows = result.fetchall()
        for r in rows:
            print(f'  user_id={r[0]}, email={r[2]}, count={r[1]}')

asyncio.run(test())
