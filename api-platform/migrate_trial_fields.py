"""数据库迁移脚本 - 添加试用字段"""
import asyncio
from src.config.database import AsyncSessionLocal
from sqlalchemy import text

async def migrate():
    async with AsyncSessionLocal() as db:
        # 检查字段是否存在
        result = await db.execute(text('''
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'users' AND column_name IN ('trial_claimed', 'trial_amount_claimed')
        '''))
        existing = [r[0] for r in result.all()]
        print(f"Existing columns: {existing}")

        if 'trial_claimed' not in existing:
            await db.execute(text('ALTER TABLE users ADD COLUMN trial_claimed BOOLEAN DEFAULT FALSE'))
            print('Added trial_claimed column')

        if 'trial_amount_claimed' not in existing:
            await db.execute(text("ALTER TABLE users ADD COLUMN trial_amount_claimed VARCHAR(20) DEFAULT '0'"))
            print('Added trial_amount_claimed column')

        await db.commit()
        print('Migration completed')

if __name__ == '__main__':
    asyncio.run(migrate())
