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
from src.core.security import hash_password, generate_api_key, generate_api_secret


async def seed_users():
    """Create test users"""
    print("Creating test users...")
    
    # 默认权限配置
    default_permissions = {
        "admin": ["*"],  # 管理员拥有所有权限
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
        
        await db.flush()
        
        # Create profiles
        profiles = [
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
        ]
        
        for profile in profiles:
            db.add(profile)
        
        await db.commit()
        
        print(f"Created users:")
        print(f"  - admin/admin@example.com (role: admin)")
        print(f"  - developer/developer@example.com (role: user)")
        print(f"  - owner/owner@example.com (role: developer)")


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
            select(User).where(User.email == "admin@example.com")
        )
        admin = result.scalar_one_or_none()
        
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
                owner_id=admin.id,
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


async def main():
    """Main function"""
    print("Seeding test data...")
    
    await seed_users()
    await seed_api_keys()
    await seed_repositories()
    
    print("Test data seeded successfully!")


if __name__ == "__main__":
    asyncio.run(main())
