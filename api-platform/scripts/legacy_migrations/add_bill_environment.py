"""
数据库迁移：为 bills 表添加 environment 字段

用于区分模拟环境和真实环境的账单数据

使用方法：
    cd api-platform
    python -m migrations.add_bill_environment
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.config.database import async_engine


async def migrate():
    """执行迁移"""
    
    async with async_engine.begin() as conn:
        # 检查字段是否已存在
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'bills' AND column_name = 'environment'
        """))
        
        if result.fetchone():
            print("✅ 字段 'environment' 已存在，跳过迁移")
            return
        
        # 添加 environment 字段
        print("📝 正在添加 'environment' 字段到 bills 表...")
        await conn.execute(text("""
            ALTER TABLE bills 
            ADD COLUMN environment VARCHAR(20) DEFAULT 'simulation'
        """))
        
        # 创建索引以提高查询性能
        print("📝 正在创建索引...")
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_bills_environment 
            ON bills (environment)
        """))
        
        # 为现有数据设置默认值
        print("📝 正在更新现有数据...")
        await conn.execute(text("""
            UPDATE bills SET environment = 'simulation' WHERE environment IS NULL
        """))
        
        print("✅ 迁移完成！")
        print("")
        print("说明：")
        print("  - 所有现有账单数据将被标记为 'simulation' (模拟环境)")
        print("  - 新创建的账单将根据 payment_mock_mode 配置自动设置环境")
        print("")


async def rollback():
    """回滚迁移"""
    
    async with async_engine.begin() as conn:
        print("📝 正在删除索引...")
        await conn.execute(text("""
            DROP INDEX IF EXISTS ix_bills_environment
        """))
        
        print("📝 正在删除 'environment' 字段...")
        await conn.execute(text("""
            ALTER TABLE bills DROP COLUMN IF EXISTS environment
        """))
        
        print("✅ 回滚完成！")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        print("开始回滚迁移...")
        asyncio.run(rollback())
    else:
        print("开始执行迁移...")
        asyncio.run(migrate())
