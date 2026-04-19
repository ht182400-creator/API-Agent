"""
Seed test data script

This script creates test data for development and testing.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from src.config.database import AsyncSessionLocal
from src.models.user import User, UserProfile
from src.models.api_key import APIKey
from src.models.repository import Repository, RepoPricing
from src.models.notification import Notification, NotificationPreference
from src.core.security import hash_password, generate_api_key, generate_api_secret


async def seed_users():
    """Create test users"""
    print("Creating test users...")
    
    # 默认权限配置
    default_permissions = {
        "super_admin": ["*"],  # 超级管理员拥有所有权限
        "admin": ["*"],  # 管理员拥有大部分权限
        "owner": ["user:read", "user:write", "api:read", "api:write", "repo:manage"],
        "developer": ["user:read", "user:write", "api:read", "api:write"],
        "user": ["user:read"],
    }
    
    async with AsyncSessionLocal() as db:
        # Check if users already exist
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            print("Users already exist, skipping...")
            return
        
        # Create super_admin user
        super_admin = User(
            username="superadmin",
            email="superadmin@example.com",
            password_hash=hash_password("super123456"),
            user_type="super_admin",
            user_status="active",
            role="super_admin",
            permissions=default_permissions["super_admin"],
            email_verified=True,
        )
        db.add(super_admin)
        
        # Create admin user
        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            user_type="admin",
            user_status="active",
            role="admin",
            permissions=default_permissions["admin"],
            email_verified=True,
        )
        db.add(admin)
        
        # Create developer user
        developer = User(
            username="developer",
            email="developer@example.com",
            password_hash=hash_password("dev123456"),
            user_type="developer",
            user_status="active",
            role="user",
            permissions=default_permissions["developer"],
            email_verified=True,
        )
        db.add(developer)
        
        # Create owner user
        owner = User(
            username="owner",
            email="owner@example.com",
            password_hash=hash_password("owner123456"),
            user_type="owner",
            user_status="active",
            role="developer",
            permissions=default_permissions["owner"],
            email_verified=True,
        )
        db.add(owner)
        
        # Create regular user
        user = User(
            username="testuser",
            email="testuser@example.com",
            password_hash=hash_password("test123456"),
            user_type="user",
            user_status="active",
            role="user",
            permissions=default_permissions["user"],
            email_verified=True,
        )
        db.add(user)
        
        await db.flush()
        
        # Create profiles
        profiles = [
            UserProfile(
                user_id=super_admin.id,
                nickname="Super Admin",
                real_name="System Super Administrator",
                company="API Platform HQ",
            ),
            UserProfile(
                user_id=admin.id,
                nickname="Admin",
                real_name="System Administrator",
                company="API Platform",
            ),
            UserProfile(
                user_id=developer.id,
                nickname="Developer",
                real_name="Test Developer",
                company="Test Company",
            ),
            UserProfile(
                user_id=owner.id,
                nickname="Owner",
                real_name="Repository Owner",
                company="Owner's Business",
            ),
            UserProfile(
                user_id=user.id,
                nickname="Test User",
                real_name="Test User",
                company="Test",
            ),
        ]
        
        for profile in profiles:
            db.add(profile)
        
        await db.commit()
        
        print(f"Created users:")
        print(f"  - superadmin/superadmin@example.com (type: super_admin, role: super_admin) - 密码: super123456")
        print(f"  - admin/admin@example.com (type: admin, role: admin) - 密码: admin123")
        print(f"  - developer/developer@example.com (type: developer, role: user) - 密码: dev123456")
        print(f"  - owner/owner@example.com (type: owner, role: developer) - 密码: owner123456")
        print(f"  - testuser/testuser@example.com (type: user, role: user) - 密码: test123456")


async def seed_api_keys():
    """Create test API keys"""
    print("Creating test API keys...")
    
    async with AsyncSessionLocal() as db:
        # Get developer user
        result = await db.execute(
            select(User).where(User.email == "developer@example.com")
        )
        developer = result.scalar_one_or_none()
        
        if not developer:
            print("Developer user not found, skipping API keys...")
            return
        
        # Create API key
        api_key_str, key_hash = generate_api_key("sk_test")
        secret = generate_api_secret()
        
        api_key = APIKey(
            user_id=developer.id,
            key_name="Test API Key",
            key_prefix="sk_test",
            key_hash=key_hash,
            secret_hash=hash_password(secret)[:64],  # Simplified
            auth_type="api_key",
            rate_limit_rpm=1000,
            rate_limit_rph=10000,
            daily_quota=100000,
            monthly_quota=1000000,
            status="active",
        )
        
        db.add(api_key)
        await db.commit()
        
        print(f"Created API Key: {api_key_str}")
        print(f"API Secret: {secret}")


async def seed_repositories():
    """Create test repositories"""
    print("Creating test repositories...")
    
    async with AsyncSessionLocal() as db:
        # Check if repositories already exist
        result = await db.execute(select(Repository).limit(1))
        if result.scalar_one_or_none():
            print("Repositories already exist, skipping...")
            return
        
        # Get owner user
        result = await db.execute(
            select(User).where(User.email == "owner@example.com")
        )
        owner = result.scalar_one_or_none()
        
        if not owner:
            print("Owner user not found, skipping repositories...")
            return
        
        # Create internal repositories
        repos = [
            {
                "name": "psychology",
                "slug": "psychology",
                "display_name": "心理问答",
                "description": "专业心理问答服务，提供智能对话和心理建议",
                "repo_type": "psychology",
                "protocol": "http",
                "endpoint_url": "http://psychology-service:8000",
            },
            {
                "name": "translation",
                "slug": "translation",
                "display_name": "多语言翻译",
                "description": "支持多种语言的翻译服务",
                "repo_type": "translation",
                "protocol": "http",
                "endpoint_url": "http://translation-service:8000",
            },
            {
                "name": "vision",
                "slug": "vision",
                "display_name": "图像识别",
                "description": "OCR文字识别和图像分析服务",
                "repo_type": "vision",
                "protocol": "http",
                "endpoint_url": "http://vision-service:8000",
            },
        ]
        
        for repo_data in repos:
            repo = Repository(
                owner_id=owner.id,
                owner_type="internal",
                status="online",
                online_at=datetime.utcnow(),
                sla_uptime="99.9",
                sla_latency_p99=500,
                **repo_data,
            )
            db.add(repo)
            await db.flush()
            
            # Create pricing
            pricing = RepoPricing(
                repo_id=repo.id,
                pricing_type="token",
                price_per_call="0.01",
                price_per_token="0.001",
                free_calls=100,
                free_tokens=1000,
            )
            db.add(pricing)
        
        await db.commit()
        print("Created repositories: psychology, translation, vision")


async def seed_notifications():
    """Create test notifications for users"""
    print("Creating test notifications...")
    
    from datetime import timedelta
    
    async with AsyncSessionLocal() as db:
        # Check if notifications already exist
        result = await db.execute(select(Notification).limit(1))
        if result.scalar_one_or_none():
            print("Notifications already exist, skipping...")
            return
        
        # Get all active users
        result = await db.execute(
            select(User).where(User.user_status == "active")
        )
        users = result.scalars().all()
        
        if not users:
            print("No users found, skipping notifications...")
            return
        
        # Notification templates
        notification_templates = [
            # 系统通知
            {
                "title": "欢迎使用API服务平台",
                "content": "感谢您注册成为我们的用户。平台提供丰富的API接口供您使用，如有疑问请联系客服。",
                "notification_type": "system",
                "priority": "normal",
                "is_unread": False,
            },
            {
                "title": "系统升级通知",
                "content": "平台将于本周日凌晨2:00-4:00进行系统升级，届时服务可能暂时不可用，请提前做好准备。",
                "notification_type": "system",
                "priority": "high",
                "is_unread": True,
            },
            # 账单通知
            {
                "title": "账单已生成",
                "content": "您2026年4月的账单已生成，当前应支付金额为 ¥128.50，请及时支付以保持服务正常运行。",
                "notification_type": "billing",
                "priority": "high",
                "is_unread": True,
            },
            {
                "title": "配额使用提醒",
                "content": "您的API配额已使用80%，剩余配额约可支持3天使用。建议您及时充值以避免服务中断。",
                "notification_type": "billing",
                "priority": "high",
                "is_unread": False,
            },
            # API通知
            {
                "title": "API Key创建成功",
                "content": "您的新API Key已成功创建。请妥善保管，不要在公开场合泄露您的密钥。",
                "notification_type": "api",
                "priority": "normal",
                "is_unread": False,
            },
            {
                "title": "API调用异常提醒",
                "content": "检测到您的API在过去1小时内有较高错误率(>5%)，请检查您的调用代码或密钥配置。",
                "notification_type": "api",
                "priority": "high",
                "is_unread": True,
            },
            # 安全通知
            {
                "title": "异地登录提醒",
                "content": "检测到您的账号在新的IP地址登录。如果这不是您本人的操作，请立即修改密码并联系客服。",
                "notification_type": "security",
                "priority": "urgent",
                "is_unread": True,
            },
        ]
        
        count = 0
        for user in users:
            # 为每个用户创建通知
            for i, template in enumerate(notification_templates):
                notification = Notification(
                    user_id=user.id,
                    title=template["title"],
                    content=template["content"],
                    notification_type=template["notification_type"],
                    priority=template["priority"],
                    status="read" if not template["is_unread"] else "unread",
                    read_at=datetime.utcnow() - timedelta(days=2) if not template["is_unread"] else None,
                    created_at=datetime.utcnow() - timedelta(hours=i * 3 + 1),
                )
                db.add(notification)
                count += 1
            
            # 创建通知偏好设置
            preference = NotificationPreference(
                user_id=user.id,
                email_enabled=True,
                in_app_enabled=True,
                push_enabled=False,
                preferences={
                    "system": True,
                    "billing": True,
                    "api": True,
                    "security": True,
                },
            )
            db.add(preference)
        
        await db.commit()
        print(f"Created {count} notifications for {len(users)} users")


async def main():
    """Main function"""
    print("Seeding test data...")
    print("=" * 50)
    
    await seed_users()
    await seed_api_keys()
    await seed_repositories()
    await seed_notifications()
    
    print("=" * 50)
    print("Test data seeded successfully!")
    print()
    print("=" * 50)
    print("测试账户列表:")
    print("=" * 50)
    print("| 用户类型      | 用户名      | 邮箱                      | 密码        |")
    print("|--------------|------------|---------------------------|-------------|")
    print("| 超级管理员    | superadmin | superadmin@example.com    | super123456 |")
    print("| 管理员        | admin      | admin@example.com         | admin123    |")
    print("| 仓库所有者    | owner      | owner@example.com         | owner123456 |")
    print("| 开发者        | developer  | developer@example.com     | dev123456   |")
    print("| 普通用户      | testuser   | testuser@example.com     | test123456  |")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
