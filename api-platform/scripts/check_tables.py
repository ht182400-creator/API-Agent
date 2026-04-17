"""Check database tables"""
import asyncio
from sqlalchemy import text
from src.config.database import async_engine

async def check():
    async with async_engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        ))
        tables = [r[0] for r in result.fetchall()]
        print("数据库表:")
        for t in tables:
            print(f"  - {t}")

if __name__ == "__main__":
    asyncio.run(check())
