import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models.user import User
from src.core.security import verify_password, hash_password
from sqlalchemy import select

async def check_admin():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres123@localhost:5432/api_platform')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == 'admin@example.com'))
        user = result.scalar_one_or_none()
        if user:
            print(f'User found:')
            print(f'  Email: {user.email}')
            print(f'  Password Hash: {user.password_hash[:50]}...' if user.password_hash else '  Password Hash: None')
            print(f'  Hash starts with $2: {user.password_hash.startswith("$2")}')
            print(f'  Hash length: {len(user.password_hash)}')
            
            # 测试密码验证
            test_pwd = 'admin123'
            is_valid = verify_password(test_pwd, user.password_hash)
            print(f'\nPassword verification test:')
            print(f'  Plain password: {test_pwd}')
            print(f'  Result: {is_valid}')
            
            # 生成新的哈希来对比
            new_hash = hash_password(test_pwd)
            print(f'\nNew hash for "admin123":')
            print(f'  {new_hash[:50]}...')
            print(f'  Starts with $2: {new_hash.startswith("$2")}')
        else:
            print('User not found!')

asyncio.run(check_admin())
