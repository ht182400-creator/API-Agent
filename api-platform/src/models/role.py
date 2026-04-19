"""Role model - 角色权限模型"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.config.database import Base


class Role(Base):
    """Role model - 角色表"""

    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 角色标识
    name = Column(String(50), unique=True, nullable=False, index=True)  # super_admin, admin, developer, user
    display_name = Column(String(100), nullable=False)  # 超级管理员, 管理员, 开发者, 普通用户
    
    # 角色描述
    description = Column(Text, nullable=True)
    
    # 权限配置
    permissions = Column(JSONB, default=list)  # ["user:read", "user:write", ...]
    is_system = Column(Boolean, default=False)  # 是否系统内置角色（不可删除/修改）
    
    # 状态
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # 优先级，数字越大权限越高
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<Role {self.name}>"


# 默认角色定义
DEFAULT_ROLES = [
    {
        "name": "super_admin",
        "display_name": "超级管理员",
        "description": "系统最高权限，拥有所有功能",
        "permissions": ["*"],  # * 表示所有权限
        "is_system": True,
        "priority": 100,
    },
    {
        "name": "admin",
        "display_name": "管理员",
        "description": "日常运营管理权限",
        "permissions": [
            "user:read", "user:write", "user:delete", "user:manage",
            "api:read", "api:write", "api:delete", "api:manage",
            "repo:read", "repo:write", "repo:delete", "repo:approve", "repo:manage",
            "billing:read", "billing:write", "billing:manage", "billing:recharge",
            "log:read", "log:all",
            "system:settings", "system:logs",
            "dev:apikeys", "dev:quota", "dev:billing",
            "owner:repo", "owner:analytics", "owner:settlement",
        ],
        "is_system": True,
        "priority": 80,
    },
    {
        "name": "owner",
        "display_name": "仓库所有者",
        "description": "API仓库所有者，可管理自己的仓库",
        "permissions": [
            "repo:read", "repo:write", "repo:delete",
            "owner:repo", "owner:analytics", "owner:settlement",
            "billing:read", "billing:manage",
            "log:read",
        ],
        "is_system": True,
        "priority": 60,
    },
    {
        "name": "developer",
        "display_name": "开发者",
        "description": "可创建API Keys，使用API服务",
        "permissions": [
            "dev:apikeys", "dev:quota", "dev:billing",
            "billing:read",
            "log:read",
            "repo:read",
        ],
        "is_system": True,
        "priority": 40,
    },
    {
        "name": "user",
        "display_name": "普通用户",
        "description": "受限权限，仅能查看",
        "permissions": [
            "dev:quota",
            "billing:read",
            "repo:read",
        ],
        "is_system": True,
        "priority": 20,
    },
]


# 权限定义（用于前端展示）
PERMISSION_DEFINITIONS = {
    # 用户管理
    "user:read": {"name": "查看用户", "group": "用户管理"},
    "user:write": {"name": "编辑用户", "group": "用户管理"},
    "user:delete": {"name": "删除用户", "group": "用户管理"},
    "user:manage": {"name": "管理所有用户", "group": "用户管理"},
    "user:role": {"name": "分配角色", "group": "用户管理"},
    
    # API Keys
    "api:read": {"name": "查看API Keys", "group": "API Keys"},
    "api:write": {"name": "创建API Keys", "group": "API Keys"},
    "api:delete": {"name": "删除API Keys", "group": "API Keys"},
    "api:manage": {"name": "管理所有API Keys", "group": "API Keys"},
    
    # 仓库管理
    "repo:read": {"name": "查看仓库", "group": "仓库管理"},
    "repo:write": {"name": "创建仓库", "group": "仓库管理"},
    "repo:delete": {"name": "删除仓库", "group": "仓库管理"},
    "repo:approve": {"name": "审核仓库", "group": "仓库管理"},
    "repo:manage": {"name": "管理所有仓库", "group": "仓库管理"},
    
    # 账单管理
    "billing:read": {"name": "查看账单", "group": "账单管理"},
    "billing:write": {"name": "编辑账单", "group": "账单管理"},
    "billing:manage": {"name": "管理所有账单", "group": "账单管理"},
    "billing:recharge": {"name": "充值", "group": "账单管理"},
    
    # 日志查看
    "log:read": {"name": "查看个人日志", "group": "日志查看"},
    "log:all": {"name": "查看所有日志", "group": "日志查看"},
    
    # 系统管理
    "system:settings": {"name": "系统设置", "group": "系统管理"},
    "system:logs": {"name": "系统日志", "group": "系统管理"},
    
    # 开发者功能
    "dev:apikeys": {"name": "API Keys管理", "group": "开发者功能"},
    "dev:quota": {"name": "配额查看", "group": "开发者功能"},
    "dev:billing": {"name": "个人账单", "group": "开发者功能"},
    
    # 仓库所有者
    "owner:repo": {"name": "仓库管理", "group": "仓库所有者"},
    "owner:analytics": {"name": "数据分析", "group": "仓库所有者"},
    "owner:settlement": {"name": "收益结算", "group": "仓库所有者"},
}
