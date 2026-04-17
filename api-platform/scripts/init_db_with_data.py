"""
数据库初始化脚本 - 包含测试数据
用于开发/测试环境数据库初始化

使用方法:
    python scripts/init_db_with_data.py          # 仅初始化
    python scripts/init_db_with_data.py --drop  # 删除重建
    python scripts/init_db_with_data.py --sample-data  # 添加示例数据
"""

import asyncio
import sys
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import uuid
import secrets

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import async_engine, AsyncSessionLocal, Base
from src.models import *  # noqa: F401, F403
from src.core.security import hash_password  # 使用统一的密码哈希


async def create_extensions():
    """创建 PostgreSQL 扩展"""
    print("Creating PostgreSQL extensions...")
    async with async_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\""))
    print("Extensions created successfully!")


async def init_db():
    """初始化数据库表"""
    print("Initializing database...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized successfully!")


async def drop_db():
    """删除所有表"""
    print("Dropping all tables...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("All tables dropped!")


async def create_test_data(session: AsyncSession):
    """创建测试数据"""
    print("Creating test data...")
    
    now = datetime.now()
    
    # ==================== 用户数据 ====================
    users = [
        User(
            id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            phone="13800000001",
            user_type="admin",
            user_status="active",
            email_verified=True,
            vip_level=3,
            vip_expire_at=now + timedelta(days=365),
            created_at=now,
            last_login_at=now,
        ),
        User(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            email="owner@example.com",
            password_hash=hash_password("owner123"),
            phone="13800000002",
            user_type="owner",
            user_status="active",
            email_verified=True,
            vip_level=2,
            vip_expire_at=now + timedelta(days=180),
            created_at=now - timedelta(days=30),
            last_login_at=now - timedelta(hours=2),
        ),
        User(
            id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            email="developer@example.com",
            password_hash=hash_password("dev123456"),
            phone="13800000003",
            user_type="developer",
            user_status="active",
            email_verified=True,
            vip_level=1,
            created_at=now - timedelta(days=15),
            last_login_at=now - timedelta(hours=1),
        ),
        User(
            id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
            email="test@example.com",
            password_hash=hash_password("test123"),
            phone="13800000004",
            user_type="developer",
            user_status="active",
            email_verified=False,
            vip_level=0,
            created_at=now - timedelta(days=7),
        ),
    ]
    
    for user in users:
        session.add(user)
    
    # ==================== 用户账户数据 ====================
    accounts = [
        Account(
            id=uuid.UUID("aaaa1111-1111-1111-1111-111111111111"),
            user_id=users[0].id,
            account_type="balance",
            balance="10000.00",
            total_recharge="10000.00",
            total_consume="0.00",
            created_at=now,
        ),
        Account(
            id=uuid.UUID("aaaa2222-2222-2222-2222-222222222222"),
            user_id=users[1].id,
            account_type="balance",
            balance="5000.00",
            total_recharge="5000.00",
            total_consume="0.00",
            created_at=now - timedelta(days=30),
        ),
        Account(
            id=uuid.UUID("aaaa3333-3333-3333-3333-333333333333"),
            user_id=users[2].id,
            account_type="balance",
            balance="100.00",
            total_recharge="100.00",
            total_consume="0.00",
            created_at=now - timedelta(days=15),
        ),
        Account(
            id=uuid.UUID("aaaa4444-4444-4444-4444-444444444444"),
            user_id=users[3].id,
            account_type="balance",
            balance="50.00",
            total_recharge="50.00",
            total_consume="0.00",
            created_at=now - timedelta(days=7),
        ),
    ]
    
    for account in accounts:
        session.add(account)
    
    # ==================== API 仓库数据 ====================
    repositories = [
        Repository(
            id=uuid.UUID("bbbb1111-1111-1111-1111-111111111111"),
            owner_id=users[1].id,
            owner_type="internal",
            name="OpenAI GPT-4 API",
            slug="openai-gpt4",
            description="OpenAI GPT-4 官方 API 接口，支持文本生成、代码编写等",
            repo_type="ai",
            protocol="http",
            endpoint_url="https://api.openai.com/v1",
            api_docs_url="https://platform.openai.com/docs",
            status="online",
            total_calls=150000,
            active_keys=25,
            avg_latency_ms=1500,
            success_rate="99.5%",
            sla_uptime="99.9%",
            sla_latency_p99=3000,
            created_at=now - timedelta(days=60),
        ),
        Repository(
            id=uuid.UUID("bbbb2222-2222-2222-2222-222222222222"),
            owner_id=users[1].id,
            owner_type="internal",
            name="Claude AI API",
            slug="anthropic-claude",
            description="Anthropic Claude AI 接口，支持长文本处理",
            repo_type="ai",
            protocol="http",
            endpoint_url="https://api.anthropic.com/v1",
            api_docs_url="https://docs.anthropic.com",
            status="online",
            total_calls=80000,
            active_keys=15,
            avg_latency_ms=2500,
            success_rate="99.8%",
            sla_uptime="99.9%",
            sla_latency_p99=5000,
            created_at=now - timedelta(days=45),
        ),
        Repository(
            id=uuid.UUID("bbbb3333-3333-3333-3333-333333333333"),
            owner_id=users[1].id,
            owner_type="internal",
            name="图像识别服务",
            slug="vision-api",
            description="基于深度学习的图像识别和分类 API",
            repo_type="ai",
            protocol="http",
            endpoint_url="https://api.example.com/vision",
            api_docs_url="https://api.example.com/docs",
            status="online",
            total_calls=30000,
            active_keys=8,
            avg_latency_ms=800,
            success_rate="99.2%",
            sla_uptime="99.5%",
            sla_latency_p99=2000,
            created_at=now - timedelta(days=30),
        ),
    ]
    
    for repo in repositories:
        session.add(repo)
    
    # ==================== API Keys 数据 ====================
    api_keys = [
        APIKey(
            id=uuid.UUID("cccc1111-1111-1111-1111-111111111111"),
            user_id=users[2].id,
            key_name="开发环境 Key",
            key_prefix="sk_test_a",
            key_hash=hashlib.sha256("sk_test_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa".encode()).hexdigest(),
            auth_type="api_key",
            rate_limit_rpm=100,
            rate_limit_rph=1000,
            daily_quota=1000,
            status="active",
            total_calls=150,
            last_call_at=now - timedelta(hours=6),
            created_at=now - timedelta(days=10),
        ),
        APIKey(
            id=uuid.UUID("cccc2222-2222-2222-2222-222222222222"),
            user_id=users[2].id,
            key_name="生产环境 Key",
            key_prefix="sk_live_A",
            key_hash=hashlib.sha256("sk_live_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA".encode()).hexdigest(),
            auth_type="api_key",
            rate_limit_rpm=500,
            rate_limit_rph=10000,
            daily_quota=50000,
            status="active",
            total_calls=50,
            last_call_at=now - timedelta(hours=1),
            created_at=now - timedelta(days=5),
        ),
        APIKey(
            id=uuid.UUID("cccc3333-3333-3333-3333-333333333333"),
            user_id=users[3].id,
            key_name="测试 Key",
            key_prefix="sk_test_b",
            key_hash=hashlib.sha256("sk_test_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb".encode()).hexdigest(),
            auth_type="api_key",
            rate_limit_rpm=50,
            rate_limit_rph=500,
            daily_quota=500,
            status="active",
            total_calls=20,
            created_at=now - timedelta(days=3),
        ),
    ]
    
    for key in api_keys:
        session.add(key)
    
    # ==================== 账单数据 ====================
    bills = [
        Bill(
            bill_no="BILL20240417001",
            user_id=users[2].id,
            bill_type="consume",
            amount="-5.50",
            balance_before="105.50",
            balance_after="100.00",
            status="completed",
            description="API 调用消费",
            source_type="api_call",
            source_id=str(api_keys[0].id),
            created_at=now - timedelta(hours=6),
        ),
        Bill(
            bill_no="BILL20240417002",
            user_id=users[2].id,
            bill_type="recharge",
            amount="100.00",
            balance_before="5.50",
            balance_after="105.50",
            status="completed",
            description="账户充值",
            source_type="manual",
            created_at=now - timedelta(days=15),
        ),
        Bill(
            bill_no="BILL20240417003",
            user_id=users[3].id,
            bill_type="consume",
            amount="-2.00",
            balance_before="52.00",
            balance_after="50.00",
            status="completed",
            description="API 调用消费",
            source_type="api_call",
            source_id=str(api_keys[2].id),
            created_at=now - timedelta(hours=12),
        ),
    ]
    
    for bill in bills:
        session.add(bill)
    
    # ==================== 配额数据 ====================
    quotas = [
        Quota(
            user_id=users[2].id,
            quota_type="daily",
            quota_limit=1000,
            quota_used=150,
            reset_type="daily",
            reset_at=now + timedelta(hours=12),
            created_at=now - timedelta(days=1),
        ),
        Quota(
            user_id=users[2].id,
            quota_type="monthly",
            quota_limit=30000,
            quota_used=5000,
            reset_type="monthly",
            reset_at=now + timedelta(days=15),
            created_at=now - timedelta(days=15),
        ),
        Quota(
            user_id=users[3].id,
            quota_type="daily",
            quota_limit=500,
            quota_used=50,
            reset_type="daily",
            reset_at=now + timedelta(hours=8),
            created_at=now - timedelta(days=3),
        ),
    ]
    
    for quota in quotas:
        session.add(quota)
    
    # ==================== 调用日志数据 ====================
    usage_logs = [
        KeyUsageLog(
            key_id=api_keys[0].id,
            user_id=users[2].id,
            repo_id=repositories[0].id,
            endpoint="/chat/completions",
            method="POST",
            status_code=200,
            latency_ms=1250,
            tokens_used=50,
            cost="0.05",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            created_at=now - timedelta(hours=6),
        ),
        KeyUsageLog(
            key_id=api_keys[1].id,
            user_id=users[2].id,
            repo_id=repositories[0].id,
            endpoint="/chat/completions",
            method="POST",
            status_code=200,
            latency_ms=2100,
            tokens_used=120,
            cost="0.12",
            ip_address="192.168.1.100",
            user_agent="Python/3.11 httpx/1.0",
            created_at=now - timedelta(hours=1),
        ),
        KeyUsageLog(
            key_id=api_keys[2].id,
            user_id=users[3].id,
            repo_id=repositories[1].id,
            endpoint="/v1/messages",
            method="POST",
            status_code=200,
            latency_ms=3500,
            tokens_used=2000,
            cost="0.50",
            ip_address="192.168.1.101",
            user_agent="Claude-SDK/1.0",
            created_at=now - timedelta(hours=2),
        ),
    ]
    
    for log in usage_logs:
        session.add(log)
    
    await session.commit()
    print("Test data created successfully!")


def print_test_accounts():
    """打印测试账户信息"""
    print("\n" + "=" * 60)
    print("TEST ACCOUNTS")
    print("=" * 60)
    print("\n| User Type | Email                   | Password    | VIP Level |")
    print("|-----------|-------------------------|-------------|-----------|")
    print("| Admin     | admin@example.com        | admin123    | 3         |")
    print("| Owner     | owner@example.com        | owner123    | 2         |")
    print("| Developer | developer@example.com    | dev123456   | 1         |")
    print("| Test      | test@example.com        | test123     | 0         |")
    print("\n" + "-" * 60)
    print("API Keys (prefix only, hash stored in DB):")
    print("  - sk_test_a*** (developer, GPT-4)")
    print("  - sk_live_A*** (developer, GPT-4, production)")
    print("  - sk_test_b*** (test user, Claude)")
    print("=" * 60 + "\n")


async def main(drop: bool = False, sample_data: bool = True):
    """主函数"""
    print("\n[Database Setup Script]")
    print("=" * 50)
    
    # 1. 创建扩展
    await create_extensions()
    
    # 2. 删除旧表(如果需要)
    if drop:
        await drop_db()
    
    # 3. 初始化数据库
    await init_db()
    
    # 4. 创建测试数据
    if sample_data:
        async with AsyncSessionLocal() as session:
            await create_test_data(session)
    
    # 5. 打印测试账户
    print_test_accounts()
    
    print("[OK] Database setup completed!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database initialization script")
    parser.add_argument("--drop", action="store_true", help="Drop all tables first")
    parser.add_argument("--no-sample-data", action="store_true", help="Skip sample data creation")
    args = parser.parse_args()
    
    asyncio.run(main(drop=args.drop, sample_data=not args.no_sample_data))
