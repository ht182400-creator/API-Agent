"""
V4.0 用户角色体系重构 - 纯数据库迁移和验证脚本

此脚本直接操作数据库，不依赖API服务：
1. 执行数据库迁移（owner -> developer）
2. 验证迁移结果
3. 检查用户类型分布
"""

import asyncio
import sys
import os
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform")

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


class DatabaseMigrationTester:
    """纯数据库迁移测试器"""

    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform"
        )
        self.results = {
            "migration": {"success": False, "details": {}},
            "verification": {"success": False, "details": {}},
            "user_type_check": {"success": False, "details": {}},
        }

    async def run_migration(self) -> dict:
        """
        执行数据库迁移
        将所有 user_type='owner' 的用户迁移到 user_type='developer'
        """
        print("\n" + "=" * 60)
        print("[Step 1] Execute Database Migration")
        print("=" * 60)

        result = {
            "owner_users_found": 0,
            "owner_users_migrated": 0,
            "already_developer": 0,
            "errors": []
        }

        try:
            engine = create_async_engine(self.database_url, echo=False)
            async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

            async with engine.begin() as conn:
                async with async_session(bind=conn) as session:
                    # 1. 查找所有 owner 用户
                    query = text("""
                        SELECT id, email, user_type, role, permissions
                        FROM users
                        WHERE user_type = 'owner'
                    """)
                    result_query = await session.execute(query)
                    owner_users = result_query.fetchall()
                    result["owner_users_found"] = len(owner_users)

                    print(f"[Migration] Found {len(owner_users)} owner users to migrate")

                    if len(owner_users) > 0:
                        # 显示要迁移的用户
                        print("\n[Migration] Users to migrate:")
                        for user in owner_users:
                            print(f"  - ID: {user[0]}, Email: {user[1]}, Type: {user[2]}, Role: {user[3]}")

                    # 2. 迁移每个 owner 用户
                    for user in owner_users:
                        user_id = user[0]
                        email = user[1]
                        current_user_type = user[2]
                        current_role = user[3]

                        try:
                            # 更新 user_type 为 developer
                            update_query = text("""
                                UPDATE users
                                SET user_type = 'developer',
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE id = :user_id
                            """)
                            await session.execute(update_query, {"user_id": user_id})

                            result["owner_users_migrated"] += 1
                            print(f"[Migration] Migrated: {email} ({current_user_type} -> developer)")

                        except Exception as e:
                            error_msg = f"Failed to migrate user {email}: {str(e)}"
                            result["errors"].append(error_msg)
                            print(f"[Migration] ERROR: {error_msg}")

                    # 3. 提交事务
                    await session.commit()

                    print(f"\n[Migration] Summary:")
                    print(f"  - Owner users found: {result['owner_users_found']}")
                    print(f"  - Users migrated: {result['owner_users_migrated']}")
                    print(f"  - Errors: {len(result['errors'])}")

                    self.results["migration"]["success"] = True
                    self.results["migration"]["details"] = result
                    await engine.dispose()
                    return result

        except Exception as e:
            error_msg = f"Migration failed: {str(e)}"
            result["errors"].append(error_msg)
            print(f"[Migration] ERROR: {error_msg}")
            self.results["migration"]["success"] = False
            self.results["migration"]["details"] = result
            return result

    async def verify_migration(self) -> dict:
        """
        验证迁移结果
        """
        print("\n" + "=" * 60)
        print("[Step 2] Verify Migration Results")
        print("=" * 60)

        result = {
            "total_users": 0,
            "user_type_distribution": {},
            "role_distribution": {},
            "owner_users_remaining": 0,
            "is_valid": True,
            "issues": []
        }

        try:
            engine = create_async_engine(self.database_url, echo=False)
            async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

            async with engine.begin() as conn:
                async with async_session(bind=conn) as session:
                    # 1. 统计总用户数
                    count_query = text("SELECT COUNT(*) FROM users")
                    count_result = await session.execute(count_query)
                    result["total_users"] = count_result.scalar()
                    print(f"[Verify] Total users: {result['total_users']}")

                    # 2. 统计 user_type 分布
                    type_query = text("""
                        SELECT user_type, COUNT(*) as count
                        FROM users
                        GROUP BY user_type
                        ORDER BY count DESC
                    """)
                    type_result = await session.execute(type_query)
                    result["user_type_distribution"] = {row[0]: row[1] for row in type_result.fetchall()}
                    print(f"[Verify] User type distribution: {result['user_type_distribution']}")

                    # 3. 统计 role 分布
                    role_query = text("""
                        SELECT role, COUNT(*) as count
                        FROM users
                        GROUP BY role
                        ORDER BY count DESC
                    """)
                    role_result = await session.execute(role_query)
                    result["role_distribution"] = {row[0]: row[1] for row in role_result.fetchall()}
                    print(f"[Verify] Role distribution: {result['role_distribution']}")

                    # 4. 检查是否还有 owner 用户
                    owner_query = text("SELECT COUNT(*) FROM users WHERE user_type = 'owner'")
                    owner_result = await session.execute(owner_query)
                    result["owner_users_remaining"] = owner_result.scalar()
                    print(f"[Verify] Owner users remaining: {result['owner_users_remaining']}")

                    # 5. 验证迁移是否正确
                    if result["owner_users_remaining"] > 0:
                        result["is_valid"] = False
                        result["issues"].append(f"Still have {result['owner_users_remaining']} owner users remaining")

                    if result["is_valid"]:
                        print("[Verify] [OK] Migration verification passed!")
                        self.results["verification"]["success"] = True
                    else:
                        print("[Verify] [ERROR] Migration verification failed!")
                        for issue in result["issues"]:
                            print(f"  - {issue}")
                        self.results["verification"]["success"] = False

                    self.results["verification"]["details"] = result
                    await engine.dispose()
                    return result

        except Exception as e:
            error_msg = f"Verification failed: {str(e)}"
            result["issues"].append(error_msg)
            print(f"[Verify] ERROR: {error_msg}")
            self.results["verification"]["success"] = False
            self.results["verification"]["details"] = result
            return result

    async def check_user_types(self) -> dict:
        """
        检查不同用户类型的详细信息
        """
        print("\n" + "=" * 60)
        print("[Step 3] Check User Type Details")
        print("=" * 60)

        result = {
            "user_details": [],
            "errors": []
        }

        try:
            engine = create_async_engine(self.database_url, echo=False)
            async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

            async with engine.begin() as conn:
                async with async_session(bind=conn) as session:
                    # 获取所有用户的详细信息
                    query = text("""
                        SELECT id, email, user_type, role, permissions
                        FROM users
                        ORDER BY user_type, role
                        LIMIT 20
                    """)
                    query_result = await session.execute(query)
                    users = query_result.fetchall()

                    print(f"[User Check] Found {len(users)} users (showing first 20):\n")

                    for user in users:
                        user_data = {
                            "id": str(user[0])[:8] + "...",
                            "email": user[1],
                            "user_type": user[2],
                            "role": user[3],
                            "permissions": user[4]
                        }
                        result["user_details"].append(user_data)
                        print(f"  Email: {user[1]}")
                        print(f"    user_type: {user[2]}")
                        print(f"    role: {user[3]}")
                        print(f"    permissions: {user[4]}")
                        print()

                    # 检查 PermissionService 预期的角色分布
                    print("[User Check] Expected role distribution after V4.0:")
                    print("  - user:        should be 'user'")
                    print("  - developer:   should be 'developer'")
                    print("  - admin:       should be 'admin'")
                    print("  - super_admin: should be 'super_admin'")
                    print("  - owner:       should NOT exist (migrated to 'developer')")

                    self.results["user_type_check"]["success"] = True
                    self.results["user_type_check"]["details"] = result
                    await engine.dispose()
                    return result

        except Exception as e:
            error_msg = f"User type check failed: {str(e)}"
            result["errors"].append(error_msg)
            print(f"[User Check] ERROR: {error_msg}")
            self.results["user_type_check"]["success"] = False
            self.results["user_type_check"]["details"] = result
            return result

    async def run_all_tests(self) -> dict:
        """运行所有测试"""
        print("\n" + "=" * 70)
        print("[TEST] V4.0 User Role System Migration - Database Migration Test")
        print("=" * 70)
        print(f"Execution time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Database: {self.database_url}")

        # 1. 执行数据库迁移
        await self.run_migration()

        # 2. 验证迁移结果
        await self.verify_migration()

        # 3. 检查用户类型详情
        await self.check_user_types()

        # 打印最终结果
        print("\n" + "=" * 70)
        print("[RESULT] Test Summary")
        print("=" * 70)

        all_passed = True
        for test_name, test_result in self.results.items():
            status = "[PASS]" if test_result["success"] else "[FAIL]"
            print(f"  {test_name}: {status}")
            if not test_result["success"]:
                all_passed = False

        print("=" * 70)
        if all_passed:
            print("[SUCCESS] All database tests passed!")
        else:
            print("[WARNING] Some tests failed, please check above output")
        print("=" * 70)

        return self.results


async def main():
    """主函数"""
    tester = DatabaseMigrationTester()
    results = await tester.run_all_tests()
    return results


if __name__ == "__main__":
    results = asyncio.run(main())
    sys.exit(0 if all(r["success"] for r in results.values()) else 1)
