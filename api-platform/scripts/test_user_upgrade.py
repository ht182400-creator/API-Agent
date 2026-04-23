"""
测试用户升级 API - 直接测试后端接口
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.database import AsyncSessionLocal, async_engine
from src.models.user import User
from sqlalchemy import select, text


async def test_upgrade():
    """测试用户升级"""
    
    print("=" * 50)
    print("TEST: User Upgrade API")
    print("=" * 50)
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. 查找测试用户
            print("\n[1] Find user...")
            result = await session.execute(
                select(User).where(User.username == "test1")
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print("ERROR: User test1 not found")
                return
            
            print(f"OK: Found user: {user.email}")
            print(f"   Current role: {user.role}")
            print(f"   Current user_type: {user.user_type}")
            
            # 2. 执行升级
            print("\n[2] Execute upgrade...")
            old_role = user.role
            old_user_type = user.user_type
            
            user.role = "developer"
            user.user_type = "developer"
            user.permissions = ["api:read", "api:write", "repo:create", "repo:manage"]
            
            await session.commit()
            
            print(f"OK: Upgrade success!")
            print(f"   Old role: {old_role} -> New role: {user.role}")
            print(f"   Old user_type: {old_user_type} -> New user_type: {user.user_type}")
            
            # 3. 验证数据库更新
            print("\n[3] Verify database update...")
            
            # 重新查询
            result = await session.execute(
                select(User).where(User.username == "test1")
            )
            user = result.scalar_one_or_none()
            
            if user:
                print(f"   Database role: {user.role}")
                print(f"   Database user_type: {user.user_type}")
                
                if user.role == "developer" and user.user_type == "developer":
                    print("\nSUCCESS: Database updated!")
                else:
                    print("\nWARNING: Database not updated as expected")
            else:
                print("ERROR: Cannot requery user")
            
        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
        finally:
            await session.close()
    
    await async_engine.dispose()


async def check_user():
    """检查用户当前状态"""
    
    print("=" * 50)
    print("CHECK: User Current Status")
    print("=" * 50)
    
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(User).where(User.username == "test1")
            )
            user = result.scalar_one_or_none()
            
            if user:
                print(f"\nUser Info:")
                print(f"  email: {user.email}")
                print(f"  role: {user.role}")
                print(f"  user_type: {user.user_type}")
                print(f"  permissions: {user.permissions}")
            else:
                print("User test1 not found")
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await session.close()
    
    await async_engine.dispose()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["check", "test"], help="Action: check=check user, test=run upgrade test")
    args = parser.parse_args()
    
    if args.action == "check":
        asyncio.run(check_user())
    else:
        asyncio.run(test_upgrade())
