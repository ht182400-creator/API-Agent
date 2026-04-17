import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models.user import User
from sqlalchemy import select

async def check_admin():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres123@localhost:5432/api_platform')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == 'admin@example.com'))
        user = result.scalar_one_or_none()
        if user:
            print(f'Email: {user.email}')
            print(f'Password Hash: {user.password_hash}')
            print(f'Hash length: {len(user.password_hash)}')
            # 检查是否是bcrypt格式 (以$2开头)
            if user.password_hash.startswith('$2'):
                print('Format: bcrypt')
            elif len(user.password_hash) == 64:
                print('Format: SHA256')
            else:
                print('Format: Unknown')
        else:
            print('User not found')

asyncio.run(check_admin())
