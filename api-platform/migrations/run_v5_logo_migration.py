"""
执行 V5.0 Logo URL 类型迁移脚本

使用方法:
    python run_v5_logo_migration.py
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config.settings import settings


async def main():
    """执行迁移"""
    print("=" * 60)
    print("V5.0 Logo URL Type Migration Runner")
    print("=" * 60)
    
    # 创建数据库连接
    engine = create_async_engine(
        settings.database_url,
        echo=True,
    )
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # 导入并运行迁移
        from migrations.versions.v5_logo_url_type import run_migration
        
        result = await run_migration(session)
        
        print("\n" + "=" * 60)
        print("Migration Result:")
        print("=" * 60)
        print(f"Success: {result.get('success', False)}")
        
        if result.get('migration'):
            print(f"Field modified: {result['migration'].get('field_modified', False)}")
        
        if result.get('verification'):
            print(f"Field type: {result['verification'].get('field_type', 'N/A')}")
        
        if result.get('errors'):
            print("Errors:")
            for error in result['errors']:
                print(f"  - {error}")
        
        if result.get('rollback'):
            print("\nRollback performed:")
            print(f"  Field reverted: {result['rollback'].get('field_reverted', False)}")
    
    await engine.dispose()
    
    print("\n" + "=" * 60)
    if result.get('success'):
        print("[OK] Migration completed successfully!")
    else:
        print("[FAIL] Migration failed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
