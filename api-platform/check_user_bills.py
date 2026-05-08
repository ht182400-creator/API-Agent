import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from datetime import datetime, timedelta

async def test():
    engine = create_async_engine('postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 北京时间 2026-05-08 的 UTC 范围
        start_utc = datetime(2026, 5, 7, 16, 0, 0)  # 北京 00:00 - 8h
        end_utc = datetime(2026, 5, 8, 15, 59, 59)   # 北京 23:59:59 - 8h
        
        # 按用户统计 5月8日的账单
        result = await session.execute(text('''
            SELECT user_id, COUNT(*) as count, MIN(created_at) as first, MAX(created_at) as last
            FROM bills 
            WHERE created_at >= :start AND created_at <= :end
              AND environment = 'production'
            GROUP BY user_id
            ORDER BY count DESC
        '''), {'start': start_utc, 'end': end_utc})
        
        print('=== 5月8日 production 环境账单按用户分布 ===')
        for r in result.fetchall():
            print(f'  user_id={r[0]}, count={r[1]}, first={r[2]}, last={r[3]}')
        
        # 查看所有 5月8日的账单（前10条）
        print('\n=== 5月8日前10条账单详情 ===')
        result2 = await session.execute(text('''
            SELECT id, user_id, bill_type, amount, description, created_at
            FROM bills 
            WHERE created_at >= :start AND created_at <= :end
              AND environment = 'production'
            ORDER BY created_at
            LIMIT 10
        '''), {'start': start_utc, 'end': end_utc})
        
        for r in result2.fetchall():
            bj_time = r[5] + timedelta(hours=8)
            print(f'  ID={r[0]}, user={r[1]}, type={r[2]}, amount={r[3]}, BJ={bj_time.strftime("%m-%d %H:%M")}')

asyncio.run(test())
