"""Database configuration - 数据库配置"""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .settings import settings

# 禁用 SQLAlchemy 的日志处理器，避免 Windows multiprocessing 子进程中写入已关闭的 stdout
# 使用 NullHandler 是 Python 日志的最佳实践，抑制所有日志输出
for _logger_name in ["sqlalchemy.engine", "sqlalchemy.engine.Engine", "sqlalchemy.pool"]:
    _logger = logging.getLogger(_logger_name)
    _logger.handlers.clear()  # 清除可能继承的 handlers
    _logger.addHandler(logging.NullHandler())
    _logger.propagate = False  # 禁止传播到父 logger

# Async database URL (for asyncpg)
DATABASE_URL_ASYNC = settings.database_url.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# Sync database URL (for migrations and scripts)
DATABASE_URL_SYNC = settings.database_url.replace(
    "postgresql://", "postgresql+psycopg2://"
)

# Create async engine
async_engine = create_async_engine(
    DATABASE_URL_ASYNC,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
)

# Create sync engine (for migrations)
engine = create_engine(
    DATABASE_URL_SYNC,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
)

# Async session factory
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency for getting database session"""
    async with AsyncSessionLocal() as session:
        try:
            # 设置会话时区为 UTC，确保时间一致性
            await session.execute(text("SET TIME ZONE 'UTC'"))
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with async_engine.begin() as conn:
        # 设置会话时区为 UTC
        await conn.execute(text("SET TIME ZONE 'UTC'"))
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    await async_engine.dispose()
