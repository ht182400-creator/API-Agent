"""Test configuration - 测试配置"""

import os
import asyncio
import pytest
from typing import AsyncGenerator, Generator

# Use PostgreSQL for integration tests (supports JSONB)
# For unit tests that don't need database, SQLite can be used
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform"
)

# Set environment variables
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Create test database engine"""
    from sqlalchemy.ext.asyncio import create_async_engine
    from src.config.database import Base
    
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async_session = sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client"""
    from src.main import app
    from src.config.database import get_db
    from httpx import ASGITransport
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    # 使用 ASGITransport 适配新版本 httpx
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create test user"""
    from src.models.user import User
    from src.core.security import hash_password
    
    user = User(
        email="test@example.com",
        password_hash=hash_password("testpassword"),
        user_type="developer",
        user_status="active",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers"""
    from src.core.security import create_access_token
    
    token = create_access_token({"sub": test_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_api_key() -> tuple[str, str]:
    """Generate test API key"""
    from src.core.security import generate_api_key
    
    api_key, key_hash = generate_api_key("sk_test")
    return api_key, key_hash
