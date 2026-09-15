#!/usr/bin/env python3
"""更新用户密码为bcrypt格式"""

import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from src.core.security import hash_password

async def update_passwords():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres123@localhost:5432/api_platform')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 更新所有用户的密码
        users_to_update = [
            ('admin@example.com', 'admin123'),
            ('owner@example.com', 'owner123'),
            ('developer@example.com', 'dev123456'),
            ('test@example.com', 'test123'),
        ]
        
        for email, password in users_to_update:
            hashed = hash_password(password)
            print(f"Updating {email}:")
            print(f"  New hash: {hashed[:50]}...")
            
            await session.execute(
                text("UPDATE users SET password_hash = :hash WHERE email = :email"),
                {"hash": hashed, "email": email}
            )
        
        await session.commit()
        print("\nAll passwords updated!")

asyncio.run(update_passwords())
