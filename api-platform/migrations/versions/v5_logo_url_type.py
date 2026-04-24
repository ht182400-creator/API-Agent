"""
V5.0 仓库自定义图标 - 数据库迁移脚本

此迁移脚本用于将 repositories 表的 logo_url 字段从 String(500) 
修改为 Text 类型，以支持 Base64 图标数据存储

迁移说明:
1. logo_url 字段用于存储仓库自定义图标（Base64 编码）
2. Base64 图片数据可能超过 500 字符限制
3. 使用 Text 类型替代 String(500) 以支持更长数据

执行时间: 2026-04-24
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def migrate_logo_url_type(db: AsyncSession) -> dict:
    """
    修改 logo_url 字段类型为 TEXT
    
    迁移前:
    - logo_url = Column(String(500), nullable=True)
    
    迁移后:
    - logo_url = Column(Text, nullable=True)
    
    Returns:
        dict: 迁移结果统计
    """
    result = {
        "field_modified": False,
        "errors": []
    }
    
    try:
        # 1. 检查当前字段类型
        check_query = text("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'repositories' AND column_name = 'logo_url'
        """)
        result_query = await db.execute(check_query)
        column_info = result_query.fetchone()
        
        if column_info:
            print(f"[Migration] Current logo_url: type={column_info[1]}, length={column_info[2]}")
        else:
            print(f"[Migration] logo_url column not found")
        
        # 2. 修改字段类型为 TEXT
        alter_query = text("""
            ALTER TABLE repositories
            ALTER COLUMN logo_url TYPE TEXT;
        """)
        await db.execute(alter_query)
        
        # 3. 提交事务
        await db.commit()
        
        result["field_modified"] = True
        print(f"[Migration] Successfully modified logo_url to TEXT type")
        
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
        "field_exists": False,
        "field_type": None,
        "is_valid": True,
        "issues": []
    }
    
    try:
        # 1. 检查字段是否存在并获取类型
        query = text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'repositories' AND column_name = 'logo_url'
        """)
        result_query = await db.execute(query)
        column_info = result_query.fetchone()
        
        if column_info:
            result["field_exists"] = True
            result["field_type"] = column_info[1]
            print(f"[Verification] logo_url field: type={column_info[1]}")
        else:
            result["field_exists"] = False
            result["is_valid"] = False
            result["issues"].append("logo_url field does not exist")
        
        # 2. 验证字段类型是否为 TEXT
        if result["field_exists"] and result["field_type"] != 'text':
            result["is_valid"] = False
            result["issues"].append(f"logo_url field type is {result['field_type']}, expected text")
        
        if result["is_valid"]:
            print("[Verification] [OK] Migration verification passed!")
        else:
            print("[Verification] [FAIL] Migration verification failed!")
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
    
    将 logo_url 字段类型恢复为 VARCHAR(500)
    
    Returns:
        dict: 回滚结果
    """
    result = {
        "field_reverted": False,
        "errors": []
    }
    
    try:
        query = text("""
            ALTER TABLE repositories
            ALTER COLUMN logo_url TYPE VARCHAR(500);
        """)
        await db.execute(query)
        await db.commit()
        
        result["field_reverted"] = True
        print(f"[Rollback] Successfully reverted logo_url to VARCHAR(500)")
        
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
    print("Starting V5.0 Logo URL Type Migration")
    print("=" * 60)
    
    # 1. 执行迁移
    print("\n[Step 1] Executing migration...")
    migration_result = await migrate_logo_url_type(db)
    
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
    print("  from migrations.versions.v5_logo_url_type import run_migration")
    print("  await run_migration(db)")
