"""
Seed roles/permissions data script

This script creates default roles with permissions for testing.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from src.config.database import AsyncSessionLocal
from src.models.role import Role, DEFAULT_ROLES


async def seed_roles():
    """Create default roles with permissions"""
    print("Creating default roles and permissions...")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        # Check if roles already exist
        result = await db.execute(select(Role).limit(1))
        if result.scalar_one_or_none():
            print("Roles already exist!")
            print("Do you want to update them? (y/N): ", end="")
            response = input()
            if response.lower() != 'y':
                print("Skipping role creation.")
                return
            else:
                # Delete existing roles
                await db.execute(select(Role))
                result = await db.execute(select(Role))
                existing_roles = result.scalars().all()
                for role in existing_roles:
                    await db.delete(role)
                print("Existing roles deleted.")
        
        # Create default roles
        for role_data in DEFAULT_ROLES:
            role = Role(
                name=role_data["name"],
                display_name=role_data["display_name"],
                description=role_data["description"],
                permissions=role_data["permissions"],
                is_system=role_data["is_system"],
                priority=role_data["priority"],
                is_active=True,
            )
            db.add(role)
            
            # Print permissions
            perms = role_data["permissions"]
            if perms == ["*"]:
                perm_display = "* (所有权限)"
            else:
                perm_display = f"{len(perms)} 项权限"
            
            print(f"  ✓ {role_data['display_name']} ({role_data['name']}) - {perm_display}")
        
        await db.commit()
        
        print()
        print("=" * 60)
        print("角色权限导入成功！")
        print("=" * 60)
        
        # Display role summary
        result = await db.execute(select(Role).order_by(Role.priority.desc()))
        roles = result.scalars().all()
        
        print()
        print("角色列表：")
        print("-" * 60)
        print(f"{'角色名称':<12} {'标识':<12} {'优先级':<8} {'权限数量'}")
        print("-" * 60)
        for role in roles:
            perm_count = "所有权限" if role.permissions == ["*"] else str(len(role.permissions))
            print(f"{role.display_name:<12} {role.name:<12} {role.priority:<8} {perm_count}")
        print("-" * 60)
        
        print()
        print("权限详情：")
        print("-" * 60)
        
        from src.models.role import PERMISSION_DEFINITIONS
        
        # Group permissions by group name
        perm_groups = {}
        for perm_key, perm_info in PERMISSION_DEFINITIONS.items():
            group = perm_info["group"]
            if group not in perm_groups:
                perm_groups[group] = []
            perm_groups[group].append((perm_key, perm_info["name"]))
        
        for group, perms in perm_groups.items():
            print(f"\n【{group}】")
            for perm_key, perm_name in perms:
                print(f"    {perm_key:<20} - {perm_name}")
        
        print()
        print("=" * 60)


async def verify_roles():
    """Verify roles exist in database"""
    print("\n验证数据库中的角色...")
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Role).order_by(Role.priority.desc()))
        roles = result.scalars().all()
        
        if not roles:
            print("数据库中没有角色数据！")
            return False
        
        print(f"找到 {len(roles)} 个角色：")
        for role in roles:
            print(f"  - {role.display_name} ({role.name})")
        
        return True


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed roles and permissions")
    parser.add_argument("--verify", action="store_true", help="Only verify roles exist")
    args = parser.parse_args()
    
    if args.verify:
        await verify_roles()
    else:
        await seed_roles()


if __name__ == "__main__":
    asyncio.run(main())
