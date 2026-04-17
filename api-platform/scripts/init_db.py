"""
Database initialization script

This script initializes the database tables.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.config.database import async_engine, Base
# 导入所有模型，确保 Base.metadata 包含所有表
from src.models import *  # noqa: F401, F403


async def init_db():
    """Initialize database tables"""
    print("Initializing database...")
    
    async with async_engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    print("Database initialized successfully!")


async def drop_db():
    """Drop all database tables"""
    print("Dropping all tables...")
    
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    print("All tables dropped!")


async def create_extensions():
    """Create PostgreSQL extensions"""
    print("Creating PostgreSQL extensions...")
    
    async with async_engine.begin() as conn:
        # Enable UUID extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
        
        # Enable pgcrypto extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\""))
    
    print("Extensions created successfully!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database initialization script")
    parser.add_argument("--drop", action="store_true", help="Drop all tables first")
    args = parser.parse_args()
    
    async def main():
        if args.drop:
            await drop_db()
        await create_extensions()
        await init_db()
    
    asyncio.run(main())
