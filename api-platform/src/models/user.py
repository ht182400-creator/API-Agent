"""User model - 用户模型"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.config.database import Base


class User(Base):
    """User model - 用户表"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 登录凭证
    username = Column(String(50), unique=True, nullable=True, index=True)  # 用户名（唯一，可选）
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)

    # 用户类型：developer（开发者）、owner（仓库所有者）、admin（管理员）
    user_type = Column(String(20), nullable=False, default="developer")
    
    # 用户状态：active（正常）、disabled（禁用）、deleted（已删除）
    user_status = Column(String(20), nullable=False, default="active")
    
    # 角色：super_admin（超级管理员）、admin（管理员）、developer（开发者）、user（普通用户）
    role = Column(String(20), nullable=False, default="user")
    
    # 细粒度权限列表，如 ["user:read", "user:write", "api:manage"]
    permissions = Column(JSONB, default=list)

    # OAuth information
    oauth_provider = Column(String(50), nullable=True)
    oauth_id = Column(String(255), nullable=True)

    # Verification status
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)

    # VIP information
    vip_level = Column(Integer, default=0)
    vip_expire_at = Column(DateTime, nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(50), nullable=True)

    # Extension fields
    extra = Column(JSONB, default=dict)

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    repositories = relationship("Repository", back_populates="owner")
    accounts = relationship("Account", back_populates="user")
    bills = relationship("Bill", back_populates="user")
    monthly_bills = relationship("MonthlyBill", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class UserProfile(Base):
    """User profile model - 用户配置表"""

    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Basic information
    nickname = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    real_name = Column(String(100), nullable=True)
    company = Column(String(200), nullable=True)
    website = Column(String(500), nullable=True)

    # Contact information
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)

    # Billing information
    billing_type = Column(String(20), default="prepaid")
    credit_limit = Column(String(20), default="0")

    # Security settings
    mfa_enabled = Column(Boolean, default=False)
    login_notify = Column(Boolean, default=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserProfile {self.nickname or self.user_id}>"
