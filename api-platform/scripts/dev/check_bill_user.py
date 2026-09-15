import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def test():
    engine = create_async_engine('postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 检查 test19 用户的 id
        result = await session.execute(text('''
            SELECT id, email, created_at FROM users WHERE email = 'test19@test19.com'
        '''))
        user = result.fetchone()
        print(f'test19 用户信息:')
        print(f'  id={user[0]}')
        print(f'  email={user[1]}')
        print(f'  created_at={user[2]}')
        
        # 检查该用户的所有账单
        result2 = await session.execute(text('''
            SELECT id, bill_type, amount, created_at
            FROM bills 
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 10
        '''), {'user_id': str(user[0])})
        
        print(f'\n该用户的账单（按时间倒序前10条）:')
        for r in result2.fetchall():
            print(f'  ID={r[0]}, type={r[1]}, amount={r[2]}, created={r[3]}')

asyncio.run(test())
