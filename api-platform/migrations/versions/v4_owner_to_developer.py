"""
V4.0 用户角色体系重构 - 数据库迁移脚本

此迁移脚本用于将现有的 owner 用户从 user_type='owner', role='developer' 
统一迁移到 user_type='developer', role='developer'

迁移说明:
1. owner 不再作为独立角色
2. owner = developer + 有仓库
3. 统一使用 user_type 进行权限判断

执行时间: 2026-04-23
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def migrate_owner_role(db: AsyncSession) -> dict:
    """
    迁移 owner 用户的角色配置
    
    迁移前:
    - user_type = 'owner'
    - role = 'developer'
    - permissions = ['user:read', 'user:write', 'api:read', 'api:write', 'repo:manage']
    
    迁移后:
    - user_type = 'developer'  # 统一使用 developer
    - role = 'developer'       # 保持不变
    - permissions = ['user:read', 'user:write', 'api:read', 'api:write', 'repo:manage']  # 保持不变
    
    Returns:
        dict: 迁移结果统计
    """
    result = {
        "owner_users_found": 0,
        "owner_users_migrated": 0,
        "already_developer": 0,
        "errors": []
    }
    
    try:
        # 1. 查找所有 owner 用户
        query = text("""
            SELECT id, email, user_type, role, permissions
            FROM users
            WHERE user_type = 'owner'
        """)
        result_query = await db.execute(query)
        owner_users = result_query.fetchall()
        result["owner_users_found"] = len(owner_users)
        
        print(f"[Migration] Found {len(owner_users)} owner users to migrate")
        
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
                await db.execute(update_query, {"user_id": user_id})
                
                result["owner_users_migrated"] += 1
                print(f"[Migration] Migrated user {email}: user_type {current_user_type} -> developer")
                
            except Exception as e:
                error_msg = f"Failed to migrate user {email}: {str(e)}"
                result["errors"].append(error_msg)
                print(f"[Migration] ERROR: {error_msg}")
        
        # 3. 提交事务
        await db.commit()
        
        print(f"[Migration] Summary:")
        print(f"  - Owner users found: {result['owner_users_found']}")
        print(f"  - Users migrated: {result['owner_users_migrated']}")
        print(f"  - Errors: {len(result['errors'])}")
        
        return result
        
    except Exception as e:
        await db.rollback()
        error_msg = f"Migration failed: {str(e)}"
        result["errors"].append(error_msg)
        print(f"[Migration] ERROR: {error_msg}")
        return result


async def verify_migration(db: AsyncSession) -> dict:
    """
    验证迁移结果
    
    Returns:
        dict: 验证结果
    """
    result = {
        "total_users": 0,
        "user_type_distribution": {},
        "owner_users_remaining": 0,
        "role_distribution": {},
        "is_valid": True,
        "issues": []
    }
    
    try:
        # 1. 统计总用户数
        query = text("SELECT COUNT(*) FROM users")
        result_query = await db.execute(query)
        result["total_users"] = result_query.scalar()
        
        # 2. 统计 user_type 分布
        query = text("""
            SELECT user_type, COUNT(*) as count
            FROM users
            GROUP BY user_type
            ORDER BY count DESC
        """)
        result_query = await db.execute(query)
        for row in result_query.fetchall():
            result["user_type_distribution"][row[0]] = row[1]
        
        # 3. 检查是否还有 owner 用户
        query = text("""
            SELECT COUNT(*) FROM users WHERE user_type = 'owner'
        """)
        result_query = await db.execute(query)
        result["owner_users_remaining"] = result_query.scalar()
        
        # 4. 统计 role 分布
        query = text("""
            SELECT role, COUNT(*) as count
            FROM users
            GROUP BY role
            ORDER BY count DESC
        """)
        result_query = await db.execute(query)
        for row in result_query.fetchall():
            result["role_distribution"][row[0]] = row[1]
        
        # 5. 验证迁移是否正确
        if result["owner_users_remaining"] > 0:
            result["is_valid"] = False
            result["issues"].append(f"Still have {result['owner_users_remaining']} owner users remaining")
        
        print(f"[Verification] Total users: {result['total_users']}")
        print(f"[Verification] User type distribution: {result['user_type_distribution']}")
        print(f"[Verification] Owner users remaining: {result['owner_users_remaining']}")
        print(f"[Verification] Role distribution: {result['role_distribution']}")
        
        if result["is_valid"]:
            print("[Verification] ✅ Migration verification passed!")
        else:
            print("[Verification] ❌ Migration verification failed!")
            for issue in result["issues"]:
                print(f"  - {issue}")
        
        return result
        
    except Exception as e:
        error_msg = f"Verification failed: {str(e)}"
        result["issues"].append(error_msg)
        result["is_valid"] = False
        print(f"[Verification] ERROR: {error_msg}")
        return result


async def rollback_migration(db: AsyncSession) -> dict:
    """
    回滚迁移（如果需要）
    
    将所有 user_type='developer' 且 role='developer' 的用户恢复为 user_type='owner'
    注意：这可能会影响非 owner 的 developer 用户
    
    Returns:
        dict: 回滚结果
    """
    result = {
        "users_rolled_back": 0,
        "errors": []
    }
    
    try:
        # 只回滚明确标记为 owner 的用户（通过额外条件判断）
        # 这里需要根据实际情况调整回滚逻辑
        query = text("""
            UPDATE users
            SET user_type = 'owner',
                updated_at = CURRENT_TIMESTAMP
            WHERE user_type = 'developer'
            AND role = 'developer'
            AND permissions::text LIKE '%repo:manage%'
        """)
        await db.execute(query)
        
        # 获取影响的行数
        result_query = await db.execute(text("SELECT COUNT(*) FROM users WHERE user_type = 'owner'"))
        result["users_rolled_back"] = result_query.scalar()
        
        await db.commit()
        
        print(f"[Rollback] Rolled back {result['users_rolled_back']} users to owner")
        
        return result
        
    except Exception as e:
        await db.rollback()
        error_msg = f"Rollback failed: {str(e)}"
        result["errors"].append(error_msg)
        print(f"[Rollback] ERROR: {error_msg}")
        return result


# 运行迁移的入口函数
async def run_migration(db: AsyncSession) -> dict:
    """
    运行完整的迁移流程
    
    1. 执行迁移
    2. 验证结果
    3. 如果验证失败，尝试回滚
    """
    print("=" * 60)
    print("Starting V4.0 User Role Migration")
    print("=" * 60)
    
    # 1. 执行迁移
    print("\n[Step 1] Executing migration...")
    migration_result = await migrate_owner_role(db)
    
    # 2. 验证迁移
    print("\n[Step 2] Verifying migration...")
    verification_result = await verify_migration(db)
    
    # 3. 如果验证失败，尝试回滚
    if not verification_result["is_valid"]:
        print("\n[Step 3] Verification failed, attempting rollback...")
        rollback_result = await rollback_migration(db)
        
        return {
            "migration": migration_result,
            "verification": verification_result,
            "rollback": rollback_result,
            "success": False
        }
    
    return {
        "migration": migration_result,
        "verification": verification_result,
        "success": True
    }


if __name__ == "__main__":
    print("This migration script should be run using Alembic or programmatically.")
    print("Example usage:")
    print("  from migrations.versions.v4_owner_to_developer import run_migration")
    print("  await run_migration(db)")
