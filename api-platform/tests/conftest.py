"""Test configuration - 测试配置"""

import os
import asyncio
import pytest
from typing import AsyncGenerator, Generator

# ---------------------------------------------------------------------------
# 测试数据库配置
# ---------------------------------------------------------------------------
# ⚠️ 重要：本文件的 test_engine fixture 会在**每个用例结束后执行 DROP ALL**，
#         因此**绝不能指向开发库或生产库**。
#
# 历史问题（已修复）：
#     默认值曾指向开发库 `api_platform`，导致"跑一次 pytest 就会清空开发库"。
#
# 现在：
#     1. 默认使用专用测试库 `api_platform_test`；
#     2. 增加安全护栏：库名不含 "test" 时直接拒绝运行（除非显式放行）。
#
# 创建测试库（只需执行一次）：
#     $env:PGPASSWORD='postgres'
#     & "D:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U postgres -d postgres `
#         -c "CREATE DATABASE api_platform_test OWNER api_user;"
#
# 如需改用其它测试库：设置环境变量 TEST_DATABASE_URL。
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform_test",
)

# 显式放行（明确知晓数据会被清空时才使用）
_ALLOW_NON_TEST_DATABASE = os.getenv("ALLOW_NON_TEST_DATABASE") == "1"


def _database_name(url: str) -> str:
    """从连接串中提取数据库名"""
    tail = url.rsplit("/", 1)[-1]
    return tail.split("?")[0].strip()


_TEST_DB_NAME = _database_name(TEST_DATABASE_URL)

if not _ALLOW_NON_TEST_DATABASE and "test" not in _TEST_DB_NAME.lower():
    raise RuntimeError(
        "\n"
        "========================================================\n"
        "  已拒绝运行测试：测试数据库名称不安全\n"
        "========================================================\n"
        f"  当前 TEST_DATABASE_URL 指向数据库：{_TEST_DB_NAME}\n"
        f"  连接串：{TEST_DATABASE_URL}\n"
        "\n"
        "  原因：tests/conftest.py 会在每个用例后 DROP 所有表，\n"
        "        指向开发/生产库会导致**数据被清空**。\n"
        "\n"
        "  解决方式（任选其一）：\n"
        "    1) 使用专用测试库（推荐）：\n"
        "       TEST_DATABASE_URL=postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform_test\n"
        "    2) 确认风险后强制放行：\n"
        "       ALLOW_NON_TEST_DATABASE=1 python -m pytest tests/\n"
        "========================================================\n"
    )

# 让被测应用使用测试库（src/config/database.py 读取 settings.database_url）
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
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("testpassword"),
        user_type="developer",
        user_status="active",
        role="user",
        permissions=["user:read", "user:write", "api:read", "api:write"],
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_admin(db_session: AsyncSession):
    """Create test admin user"""
    from src.models.user import User
    from src.core.security import hash_password
    
    admin = User(
        username="testadmin",
        email="admin@test.com",
        password_hash=hash_password("admin123"),
        user_type="admin",
        user_status="active",
        role="admin",
        permissions=["*"],
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers"""
    from src.core.security import create_access_token
    
    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_api_key() -> tuple[str, str]:
    """Generate test API key"""
    from src.core.security import generate_api_key
    
    api_key, key_hash = generate_api_key("sk_test")
    return api_key, key_hash
