import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from datetime import datetime, timedelta

async def test():
    engine = create_async_engine('postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        user_id = "29a6754a-6856-4d59-ab15-5b301ab86447"
        
        # 查看该用户所有 5月8日的记录（原始 UTC 时间）
        result = await session.execute(text('''
            SELECT id, amount, created_at
            FROM bills 
            WHERE user_id = :user_id
              AND environment = 'production'
              AND created_at >= '2026-05-07 16:00:00'
              AND created_at <= '2026-05-08 15:59:59'
            ORDER BY created_at
        '''), {'user_id': user_id})
        
        print('=== test19 用户 5月8日账单（UTC时间）===')
        for r in result.fetchall():
            utc = r[2]
            bj = utc + timedelta(hours=8)
            print(f'ID={r[0]}, amount={r[1]}, UTC={utc}, 北京={bj}')
        
        # 检查是否有其他 5月8日的记录
        print('\n=== 该用户所有账单（按时间倒序前10条）===')
        result2 = await session.execute(text('''
            SELECT id, amount, created_at
            FROM bills 
            WHERE user_id = :user_id
              AND environment = 'production'
            ORDER BY created_at DESC
            LIMIT 10
        '''), {'user_id': user_id})
        
        for r in result2.fetchall():
            utc = r[2]
            bj = utc + timedelta(hours=8)
            print(f'ID={r[0]}, amount={r[1]}, UTC={utc}, 北京={bj}')

asyncio.run(test())
