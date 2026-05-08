import requests
import json

# 测试 API
url = "http://localhost:8000/api/v1/billing/bills"
params = {
    "page": 1,
    "page_size": 20,
    "start_date": "2026-05-08",
    "end_date": "2026-05-08"
}

# 需要登录获取 token
# 这里直接用测试脚本调用

headers = {
    "Content-Type": "application/json"
}

# 获取 token
login_url = "http://localhost:8000/api/v1/auth/login"
login_data = {
    "username": "test@example.com",  # 需要替换为实际用户名
    "password": "password123"
}

try:
    # 先尝试获取用户列表确认是否有其他用户
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text
    import asyncio
    
    async def get_user():
        engine = create_async_engine('postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform')
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            result = await session.execute(text('''
                SELECT id, email, created_at FROM users ORDER BY created_at LIMIT 5
            '''))
            print("=== 最近创建的用户 ===")
            for r in result.fetchall():
                print(f"  ID={r[0]}, email={r[1]}, created={r[2]}")
    
    asyncio.run(get_user())
except Exception as e:
    print(f"Error: {e}")
