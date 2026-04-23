"""
统一权限检查服务

提供一致的权限检查方式，替代散落在各处的硬编码检查

使用方式:
    from src.services.permission_service import PermissionService, UserRole
    
    # 检查用户类型
    permission_service = PermissionService()
    if permission_service.is_admin(user):
        ...
    
    # 检查权限
    if permission_service.has_permission(user, "repo:write"):
        ...
    
    # 检查是否为仓库所有者（有仓库的开发者）
    if permission_service.is_repo_owner(user):
        ...
"""

from typing import Optional, List
from enum import Enum
from src.models.user import User


class UserRole(str, Enum):
    """用户角色枚举 - 统一使用此枚举"""
    USER = "user"                    # 普通用户
    DEVELOPER = "developer"         # API开发者
    ADMIN = "admin"                  # 管理员
    SUPER_ADMIN = "super_admin"      # 超级管理员


class PermissionService:
    """
    统一权限检查服务
    
    设计原则:
    1. 统一使用 user_type 字段判断角色
    2. role 字段保留用于历史兼容（不再作为主要判断依据）
    3. owner 不作为独立角色，是 developer 的一种业务状态
    """
    
    # 管理员角色列表
    ADMIN_ROLES = [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]
    
    # 可以创建仓库的角色
    REPO_CREATOR_ROLES = [UserRole.DEVELOPER.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]
    
    @staticmethod
    def get_user_role(user: User) -> str:
        """
        获取用户的统一角色
        
        兼容逻辑:
        - 如果 user_type 是有效角色，返回 user_type
        - 否则返回 role
        - 最后默认为 user
        
        Args:
            user: 用户对象
            
        Returns:
            统一后的角色字符串
        """
        valid_roles = [r.value for r in UserRole]
        
        if user.user_type in valid_roles:
            return user.user_type
        
        if user.role in valid_roles:
            return user.role
        
        return UserRole.USER.value
    
    @staticmethod
    def is_admin(user: User) -> bool:
        """检查是否为管理员或超级管理员"""
        role = PermissionService.get_user_role(user)
        return role in PermissionService.ADMIN_ROLES
    
    @staticmethod
    def is_super_admin(user: User) -> bool:
        """检查是否为超级管理员"""
        role = PermissionService.get_user_role(user)
        return role == UserRole.SUPER_ADMIN.value
    
    @staticmethod
    def is_developer(user: User) -> bool:
        """
        检查是否为开发者或更高级别
        
        开发者包括:
        - developer: API开发者
        - admin: 管理员（也可以创建仓库）
        - super_admin: 超级管理员
        """
        role = PermissionService.get_user_role(user)
        return role in [
            UserRole.DEVELOPER.value,
            UserRole.ADMIN.value,
            UserRole.SUPER_ADMIN.value
        ]
    
    @staticmethod
    def is_user(user: User) -> bool:
        """检查是否为普通用户"""
        role = PermissionService.get_user_role(user)
        return role == UserRole.USER.value
    
    @staticmethod
    def can_create_repo(user: User) -> bool:
        """
        检查是否可以创建仓库
        
        可以创建仓库的角色:
        - developer: API开发者
        - admin: 管理员
        - super_admin: 超级管理员
        
        注意: 普通用户(user)不能创建仓库
        """
        role = PermissionService.get_user_role(user)
        return role in PermissionService.REPO_CREATOR_ROLES
    
    @staticmethod
    def has_permission(user: User, permission: str) -> bool:
        """
        检查是否拥有指定权限
        
        Args:
            user: 用户对象
            permission: 权限字符串，如 "repo:write"
            
        Returns:
            是否拥有权限
        """
        # 超级管理员拥有所有权限
        if PermissionService.is_super_admin(user):
            return True
        
        # 检查用户的权限列表
        user_permissions = user.permissions or []
        
        # * 表示所有权限
        if "*" in user_permissions:
            return True
        
        return permission in user_permissions
    
    @staticmethod
    def get_role_display_name(user_type: str) -> str:
        """
        获取角色显示名称
        
        Args:
            user_type: 角色类型
            
        Returns:
            显示名称
        """
        display_names = {
            UserRole.USER.value: "普通用户",
            UserRole.DEVELOPER.value: "API开发者",
            UserRole.ADMIN.value: "管理员",
            UserRole.SUPER_ADMIN.value: "超级管理员",
        }
        return display_names.get(user_type, "未知角色")
    
    @staticmethod
    def get_role_description(user_type: str) -> str:
        """
        获取角色描述
        
        Args:
            user_type: 角色类型
            
        Returns:
            角色描述
        """
        descriptions = {
            UserRole.USER.value: "可充值余额、调用API服务",
            UserRole.DEVELOPER.value: "可创建API仓库并获得收益分成",
            UserRole.ADMIN.value: "可管理平台运营",
            UserRole.SUPER_ADMIN.value: "拥有平台最高权限",
        }
        return descriptions.get(user_type, "")


# 默认权限配置
DEFAULT_PERMISSIONS = {
    UserRole.USER.value: [
        "billing:read",
        "repo:read",
    ],
    UserRole.DEVELOPER.value: [
        "billing:read",
        "billing:recharge",
        "repo:read",
        "repo:write",  # 可以创建仓库
        "api:read",
        "api:write",
        "api:delete",
        "log:read",
    ],
    UserRole.ADMIN.value: [
        "billing:read",
        "billing:write",
        "billing:manage",
        "billing:recharge",
        "repo:read",
        "repo:write",
        "repo:delete",
        "repo:approve",
        "repo:manage",
        "api:read",
        "api:write",
        "api:delete",
        "api:manage",
        "user:read",
        "user:write",
        "user:delete",
        "user:manage",
        "log:read",
        "log:all",
        "system:settings",
        "system:logs",
    ],
    UserRole.SUPER_ADMIN.value: [
        "*",  # 所有权限
    ],
}
