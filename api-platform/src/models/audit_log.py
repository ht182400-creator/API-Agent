"""Audit Log model - 审计日志模型"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, DateTime, Text, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.config.database import Base


class AuditLog(Base):
    """Audit Log model - 审计日志表"""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 操作者信息
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    username = Column(String(100), nullable=True, index=True)
    user_type = Column(String(20), nullable=True)  # super_admin, admin, owner, developer, user
    
    # 操作信息
    action = Column(String(100), nullable=False, index=True)  # create, update, delete, login, logout, etc.
    resource_type = Column(String(50), nullable=False, index=True)  # user, api_key, repository, system, etc.
    resource_id = Column(String(100), nullable=True, index=True)
    
    # 操作详情
    description = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # 变更前后数据（JSON格式）
    old_data = Column(JSONB, default=dict)
    new_data = Column(JSONB, default=dict)
    
    # 状态和结果
    status = Column(String(20), default="success")  # success, failed
    error_message = Column(Text, nullable=True)
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 复合索引
    __table_args__ = (
        Index('idx_audit_user_time', 'user_id', 'created_at'),
        Index('idx_audit_resource_time', 'resource_type', 'created_at'),
        Index('idx_audit_action_time', 'action', 'created_at'),
    )

    def __repr__(self):
        return f"<AuditLog {self.action} {self.resource_type} by {self.username}>"


# 常用操作类型
class AuditAction:
    """审计操作类型常量"""
    # 用户相关
    USER_LOGIN = "user:login"
    USER_LOGOUT = "user:logout"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_DISABLE = "user:disable"
    USER_ENABLE = "user:enable"
    USER_ROLE_CHANGE = "user:role_change"
    USER_PERMISSION_CHANGE = "user:permission_change"
    
    # API Key 相关
    API_KEY_CREATE = "api_key:create"
    API_KEY_UPDATE = "api_key:update"
    API_KEY_DELETE = "api_key:delete"
    API_KEY_REVOKE = "api_key:revoke"
    
    # 仓库相关
    REPO_CREATE = "repo:create"
    REPO_UPDATE = "repo:update"
    REPO_DELETE = "repo:delete"
    REPO_APPROVE = "repo:approve"
    REPO_REJECT = "repo:reject"
    
    # 系统相关
    SYSTEM_CONFIG_UPDATE = "system:config_update"
    SYSTEM_BACKUP = "system:backup"
    SYSTEM_RESTORE = "system:restore"
    
    # 账单相关
    BILLING_RECHARGE = "billing:recharge"
    BILLING_REFUND = "billing:refund"


# 资源类型
class ResourceType:
    """资源类型常量"""
    USER = "user"
    API_KEY = "api_key"
    REPOSITORY = "repository"
    BILL = "bill"
    NOTIFICATION = "notification"
    SYSTEM = "system"
    ROLE = "role"
    PERMISSION = "permission"
