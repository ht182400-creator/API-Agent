#!/usr/bin/env python3
"""检查数据库中的密码哈希格式"""

import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def check_passwords():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres123@localhost:5432/api_platform')
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT email, password_hash, LENGTH(password_hash) as hash_len FROM users LIMIT 5"))
        rows = result.fetchall()
        print("用户密码哈希检查:")
        print("-" * 80)
        for row in rows:
            email = row[0]
            pwd_hash = row[1] if row[1] else "NULL"
            hash_len = row[2] if row[2] else 0
            
            if pwd_hash and len(pwd_hash) > 0:
                if pwd_hash.startswith('$2'):
                    fmt = "bcrypt"
                elif len(pwd_hash) == 64:
                    fmt = "SHA256"
                else:
                    fmt = "Unknown"
            else:
                fmt = "No hash"
            
            print(f"Email: {email}")
            print(f"  Hash: {pwd_hash[:50]}..." if pwd_hash and len(pwd_hash) > 50 else f"  Hash: {pwd_hash}")
            print(f"  Format: {fmt}, Length: {hash_len}")
            print()

asyncio.run(check_passwords())
