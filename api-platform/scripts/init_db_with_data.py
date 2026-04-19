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
from src.utils.crypto import encrypt_api_key  # 用于加密存储 API key


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
    # 默认权限配置
    default_permissions = {
        "admin": ["*"],  # 管理员拥有所有权限
        "owner": ["user:read", "user:write", "api:read", "api:write", "repo:manage"],
        "developer": ["user:read", "user:write", "api:read", "api:write"],
        "user": ["user:read"],
    }
    
    users = [
        User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            username="superadmin",
            email="superadmin@example.com",
            password_hash=hash_password("super123456"),
            phone="13800000000",
            user_type="super_admin",
            user_status="active",
            role="super_admin",  # 角色：超级管理员
            permissions=["*"],  # 拥有所有权限
            email_verified=True,
            vip_level=3,
            vip_expire_at=now + timedelta(days=365),
            created_at=now,
            last_login_at=now,
        ),
        User(
            id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            username="admin",
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            phone="13800000001",
            user_type="admin",
            user_status="active",
            role="admin",  # 角色：管理员
            permissions=default_permissions["admin"],
            email_verified=True,
            vip_level=3,
            vip_expire_at=now + timedelta(days=365),
            created_at=now,
            last_login_at=now,
        ),
        User(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            username="owner",
            email="owner@example.com",
            password_hash=hash_password("owner123"),
            phone="13800000002",
            user_type="owner",
            user_status="active",
            role="developer",  # 角色：开发者（仓库所有者）
            permissions=default_permissions["owner"],
            email_verified=True,
            vip_level=2,
            vip_expire_at=now + timedelta(days=180),
            created_at=now - timedelta(days=30),
            last_login_at=now - timedelta(hours=2),
        ),
        User(
            id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            username="developer",
            email="developer@example.com",
            password_hash=hash_password("dev123456"),
            phone="13800000003",
            user_type="developer",
            user_status="active",
            role="user",  # 角色：普通用户
            permissions=default_permissions["developer"],
            email_verified=True,
            vip_level=1,
            created_at=now - timedelta(days=15),
            last_login_at=now - timedelta(hours=1),
        ),
        User(
            id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
            username="test",
            email="test@example.com",
            password_hash=hash_password("test123"),
            phone="13800000004",
            user_type="user",  # 普通用户
            user_status="active",
            role="user",  # 角色：普通用户
            permissions=default_permissions["user"],
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
    # 定义完整的 API key（用于加密存储）
    test_keys = [
        "sk_test_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",  # 32字节 hex
        "sk_live_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",  # 32字节 hex
        "sk_test_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",  # 32字节 hex
    ]
    
    api_keys = [
        APIKey(
            id=uuid.UUID("cccc1111-1111-1111-1111-111111111111"),
            user_id=users[2].id,
            key_name="开发环境 Key",
            key_prefix="sk_test_a",
            key_hash=hashlib.sha256(test_keys[0].encode()).hexdigest(),
            encrypted_key=encrypt_api_key(test_keys[0]),  # 加密存储完整 key
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
            key_hash=hashlib.sha256(test_keys[1].encode()).hexdigest(),
            encrypted_key=encrypt_api_key(test_keys[1]),  # 加密存储完整 key
            auth_type="api_key",
            rate_limit_rpm=500,
            rate_limit_rph=10000,
            daily_quota=50000,
            status="active",
            total_calls=50,
            last_call_at=now - timedelta(hours=1),
            created_at=now - timedelta(days=5),
        ),
        # test 用户是普通用户，不分配 API Key
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
        # test 用户是普通用户，无 API Key，无消费账单
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
        # test 用户是普通用户，不分配 API Key，无调用日志
    ]
    
    for log in usage_logs:
        session.add(log)
    
    # ==================== 角色数据 ====================
    roles = [
        Role(
            id=uuid.UUID("dddd1111-1111-1111-1111-111111111111"),
            name="super_admin",
            display_name="超级管理员",
            description="系统最高权限，拥有所有功能",
            permissions=["*"],
            is_system=True,
            is_active=True,
            priority=100,
            created_at=now,
        ),
        Role(
            id=uuid.UUID("dddd2222-2222-2222-2222-222222222222"),
            name="admin",
            display_name="管理员",
            description="日常运营管理权限",
            permissions=[
                "user:read", "user:write", "user:delete", "user:manage",
                "api:read", "api:write", "api:delete", "api:manage",
                "repo:read", "repo:write", "repo:delete", "repo:approve", "repo:manage",
                "billing:read", "billing:write", "billing:manage", "billing:recharge",
                "log:read", "log:all",
                "system:settings", "system:logs",
                "dev:apikeys", "dev:quota", "dev:billing",
                "owner:repo", "owner:analytics", "owner:settlement",
            ],
            is_system=True,
            is_active=True,
            priority=80,
            created_at=now,
        ),
        Role(
            id=uuid.UUID("dddd3333-3333-3333-3333-333333333333"),
            name="owner",
            display_name="仓库所有者",
            description="API仓库所有者，可管理自己的仓库",
            permissions=[
                "repo:read", "repo:write", "repo:delete",
                "owner:repo", "owner:analytics", "owner:settlement",
                "billing:read", "billing:manage",
                "log:read",
            ],
            is_system=True,
            is_active=True,
            priority=60,
            created_at=now,
        ),
        Role(
            id=uuid.UUID("dddd4444-4444-4444-4444-444444444444"),
            name="developer",
            display_name="开发者",
            description="可创建API Keys，使用API服务",
            permissions=[
                "dev:apikeys", "dev:quota", "dev:billing",
                "billing:read",
                "log:read",
                "repo:read",
            ],
            is_system=True,
            is_active=True,
            priority=40,
            created_at=now,
        ),
        Role(
            id=uuid.UUID("dddd5555-5555-5555-5555-555555555555"),
            name="user",
            display_name="普通用户",
            description="受限权限，仅能查看",
            permissions=[
                "dev:quota",
                "billing:read",
                "repo:read",
            ],
            is_system=True,
            is_active=True,
            priority=20,
            created_at=now,
        ),
    ]
    
    for role in roles:
        session.add(role)
    
    # ==================== 系统配置数据 ====================
    configs = [
        # 通用设置
        SystemConfig(category="general", key="site_name", value="API Platform", value_type="string", label="平台名称", is_system=True),
        SystemConfig(category="general", key="site_url", value="https://api.example.com", value_type="string", label="平台地址", is_system=True),
        SystemConfig(category="general", key="support_email", value="support@example.com", value_type="string", label="支持邮箱", is_system=True),
        SystemConfig(category="general", key="timezone", value="Asia/Shanghai", value_type="string", label="时区", options=["Asia/Shanghai", "America/New_York", "Europe/London"], is_system=True),
        SystemConfig(category="general", key="language", value="zh-CN", value_type="string", label="默认语言", options=["zh-CN", "en-US"], is_system=True),
        
        # 安全设置
        SystemConfig(category="security", key="password_min_length", value="8", value_type="number", label="密码最小长度", is_system=True),
        SystemConfig(category="security", key="password_require_uppercase", value="true", value_type="boolean", label="必须包含大写字母", is_system=True),
        SystemConfig(category="security", key="password_require_number", value="true", value_type="boolean", label="必须包含数字", is_system=True),
        SystemConfig(category="security", key="password_require_special", value="true", value_type="boolean", label="必须包含特殊字符", is_system=True),
        SystemConfig(category="security", key="session_timeout", value="30", value_type="number", label="会话超时时间(分钟)", is_system=True),
        SystemConfig(category="security", key="max_login_attempts", value="5", value_type="number", label="最大登录失败次数", is_system=True),
        SystemConfig(category="security", key="enable_mfa", value="false", value_type="boolean", label="启用双因素认证", is_system=True),
        SystemConfig(category="security", key="enable_captcha", value="true", value_type="boolean", label="启用验证码", is_system=True),
        
        # API设置
        SystemConfig(category="api", key="default_rate_limit_rpm", value="60", value_type="number", label="默认API限流(RPM)", is_system=True),
        SystemConfig(category="api", key="default_daily_quota", value="1000", value_type="number", label="默认每日配额", is_system=True),
        SystemConfig(category="api", key="key_prefix", value="sk", value_type="string", label="API Key前缀", is_system=True),
        SystemConfig(category="api", key="key_length", value="32", value_type="number", label="API Key长度", is_system=True),
        
        # 日志设置
        SystemConfig(category="logging", key="level", value="INFO", value_type="string", label="日志级别", options=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], is_system=True),
        SystemConfig(category="logging", key="retention_days", value="30", value_type="number", label="日志保留天数", is_system=True),
        SystemConfig(category="logging", key="enable_audit", value="true", value_type="boolean", label="启用审计日志", is_system=True),
        SystemConfig(category="logging", key="enable_metrics", value="true", value_type="boolean", label="启用性能指标", is_system=True),
        
        # 缓存设置
        SystemConfig(category="cache", key="type", value="memory", value_type="string", label="缓存类型", options=["redis", "memcached", "memory"], is_system=True),
        SystemConfig(category="cache", key="ttl", value="3600", value_type="number", label="缓存TTL(秒)", is_system=True),
        
        # 限流设置
        SystemConfig(category="rate_limit", key="enabled", value="true", value_type="boolean", label="启用限流", is_system=True),
        SystemConfig(category="rate_limit", key="default_rpm", value="60", value_type="number", label="默认RPM", is_system=True),
        SystemConfig(category="rate_limit", key="default_rph", value="1000", value_type="number", label="默认RPH", is_system=True),
    ]
    
    for config in configs:
        session.add(config)
    
    # ==================== 审计日志数据 ====================
    audit_logs = [
        AuditLog(
            id=uuid.UUID("eeee1111-1111-1111-1111-111111111111"),
            user_id=users[0].id,
            username="superadmin",
            user_type="super_admin",
            action="user:login",
            resource_type="system",
            description="超级管理员登录系统",
            ip_address="192.168.1.1",
            status="success",
            created_at=now - timedelta(minutes=5),
        ),
        AuditLog(
            id=uuid.UUID("eeee2222-2222-2222-2222-222222222222"),
            user_id=users[0].id,
            username="superadmin",
            user_type="super_admin",
            action="user:create",
            resource_type="user",
            resource_id=str(users[1].id),
            description="创建管理员账户 admin@example.com",
            ip_address="192.168.1.1",
            status="success",
            created_at=now - timedelta(minutes=4),
        ),
        AuditLog(
            id=uuid.UUID("eeee3333-3333-3333-3333-333333333333"),
            user_id=users[1].id,
            username="admin",
            user_type="admin",
            action="user:update",
            resource_type="user",
            resource_id=str(users[3].id),
            description="更新开发者 developer 的VIP等级为1",
            ip_address="192.168.1.2",
            status="success",
            created_at=now - timedelta(hours=1),
        ),
        AuditLog(
            id=uuid.UUID("eeee4444-4444-4444-4444-444444444444"),
            user_id=users[1].id,
            username="admin",
            user_type="admin",
            action="repo:approve",
            resource_type="repository",
            resource_id=str(repositories[0].id),
            description="审核通过仓库 OpenAI GPT-4 API",
            ip_address="192.168.1.2",
            status="success",
            created_at=now - timedelta(hours=2),
        ),
        AuditLog(
            id=uuid.UUID("eeee5555-5555-5555-5555-555555555555"),
            user_id=users[2].id,
            username="owner",
            user_type="owner",
            action="api_key:create",
            resource_type="api_key",
            resource_id=str(api_keys[0].id),
            description="创建 API Key: 开发环境 Key",
            ip_address="192.168.1.3",
            status="success",
            created_at=now - timedelta(days=10),
        ),
        AuditLog(
            id=uuid.UUID("eeee6666-6666-6666-6666-666666666666"),
            user_id=users[0].id,
            username="superadmin",
            user_type="super_admin",
            action="system:config_update",
            resource_type="system",
            description="更新系统配置: 日志级别为 INFO",
            old_data={"logging.level": "DEBUG"},
            new_data={"logging.level": "INFO"},
            ip_address="192.168.1.1",
            status="success",
            created_at=now - timedelta(hours=6),
        ),
        AuditLog(
            id=uuid.UUID("eeee7777-7777-7777-7777-777777777777"),
            user_id=users[3].id,
            username="developer",
            user_type="developer",
            action="billing:recharge",
            resource_type="bill",
            description="账户充值 50.00 元",
            ip_address="192.168.1.4",
            status="success",
            created_at=now - timedelta(days=7),
        ),
    ]
    
    for audit_log in audit_logs:
        session.add(audit_log)
    
    await session.commit()
    print("Test data created successfully!")


def print_test_accounts():
    """打印测试账户信息"""
    print("\n" + "=" * 80)
    print("TEST ACCOUNTS")
    print("=" * 80)
    print("\n支持两种登录方式：username 或 email")
    print("\n| User Type | Username    | Email                      | Password     | Role        | VIP |")
    print("|-----------|-------------|----------------------------|--------------|-------------|-----|")
    print("| SuperAdmin| superadmin  | superadmin@example.com     | super123456  | super_admin | 3   |")
    print("| Admin     | admin       | admin@example.com         | admin123     | admin       | 3   |")
    print("| Owner     | owner       | owner@example.com         | owner123     | developer   | 2   |")
    print("| Developer | developer   | developer@example.com     | dev123456    | user        | 1   |")
    print("| Test      | test        | test@example.com          | test123      | user        | 0   |")
    print("\n" + "-" * 80)
    print("登录示例:")
    print("  - 用户名登录: username=superadmin, password=super123456")
    print("  - 邮箱登录:   email=superadmin@example.com, password=super123456")
    print("\n" + "-" * 80)
    print("用户类型说明:")
    print("  - super_admin: 超级管理员，系统最高权限")
    print("  - admin:       管理员，拥有大部分管理权限")
    print("  - owner:       仓库所有者，管理 API 仓库")
    print("  - developer:   开发者，可创建 API Keys、使用 API")
    print("  - user:        普通用户，仅能查看，不能创建 API Keys")
    print("\n" + "-" * 80)
    print("API Keys (完整 key，支持查看功能):")
    print("  - sk_test_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (developer, GPT-4)")
    print("  - sk_live_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA (developer, GPT-4, production)")
    print("  注意：完整 key 可通过前端界面点击「查看」按钮获取")
    print("=" * 80 + "\n")


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
