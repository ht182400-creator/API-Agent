"""Quick database migration test"""
import asyncio
import sys
import os
# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def test():
    db_url = 'postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform'
    print("Connecting to database...")
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        async with async_session(bind=conn) as session:
            # 1. Find owner users
            q = text("SELECT id, email, user_type, role FROM users WHERE user_type = 'owner'")
            r = await session.execute(q)
            owners = r.fetchall()
            print("Found", len(owners), "owner users")
            for u in owners:
                print("  -", u[1], ":", u[2], "/", u[3])

            # 2. Migrate owner to developer
            if owners:
                update = text("UPDATE users SET user_type = 'developer', updated_at = CURRENT_TIMESTAMP WHERE user_type = 'owner'")
                await session.execute(update)
                await session.commit()
                print("Migrated", len(owners), "users")

            # 3. Verify
            v = text("SELECT user_type, COUNT(*) FROM users GROUP BY user_type ORDER BY user_type")
            vr = await session.execute(v)
            print("\nUser type distribution:")
            for row in vr.fetchall():
                print("  ", row[0], ":", row[1])

    await engine.dispose()

    # 4. Check permission service
    print("\nPermissionService Test:")
    from src.services.permission_service import PermissionService, UserRole, DEFAULT_PERMISSIONS
    print("  UserRole enum:", [r.value for r in UserRole])
    print("  DEFAULT_PERMISSIONS keys:", list(DEFAULT_PERMISSIONS.keys()))

    # 验证没有 owner 在 UserRole 中
    if "owner" not in [r.value for r in UserRole]:
        print("  [OK] 'owner' is not a valid role in PermissionService")
    else:
        print("  [ERROR] 'owner' should not be in UserRole!")

if __name__ == "__main__":
    asyncio.run(test())
