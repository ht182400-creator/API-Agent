import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def test():
    engine = create_async_engine('postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(text('''
            SELECT email, user_type, created_at FROM users 
            WHERE email LIKE 'test%@test%.com'
            ORDER BY created_at
        '''))
        
        print('=== test 用户列表 ===')
        for r in result.fetchall():
            print(f'email={r[0]}, type={r[1]}, created={r[2]}')

asyncio.run(test())
