"""Super Admin API - 超级管理员专用接口"""

from typing import Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_, cast, Numeric
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.user import User
from src.models.api_key import APIKey
from src.models.repository import Repository
from src.models.billing import Account, Bill
from src.models.audit_log import AuditLog, AuditAction, ResourceType
from src.models.system_config import SystemConfig, ConfigCategory, DEFAULT_CONFIGS
from src.models.role import Role, DEFAULT_ROLES
from src.schemas.response import BaseResponse, PaginatedResponse
from src.services.auth_service import get_current_super_admin_user

router = APIRouter(tags=["超级管理员"])


# ==================== 统计接口 ====================

class DashboardStats(BaseModel):
    """仪表板统计数据"""
    total_users: int
    active_users: int
    total_repos: int
    total_api_keys: int
    total_revenue: float
    user_type_stats: List[dict]


class RecentActivity(BaseModel):
    """最近活动"""
    id: str
    action: str
    username: str
    resource_type: str
    resource_id: Optional[str]
    description: Optional[str]
    ip_address: Optional[str]
    status: str
    created_at: datetime


@router.get("/dashboard/stats", response_model=BaseResponse[DashboardStats])
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_super_admin_user),
):
    """
    获取仪表板统计数据
    
    返回系统全局统计信息，包括用户数、活跃用户数、仓库数、API Keys数、总收入等。
    """
    # 统计用户总数
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0
    
    # 统计活跃用户（30天内有登录）
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users_result = await db.execute(
        select(func.count(User.id)).where(
            User.last_login_at >= thirty_days_ago
        )
    )
    active_users = active_users_result.scalar() or 0
    
    # 统计仓库总数
    repos_result = await db.execute(select(func.count(Repository.id)))
    total_repos = repos_result.scalar() or 0
    
    # 统计 API Keys 总数
    keys_result = await db.execute(select(func.count(APIKey.id)))
    total_api_keys = keys_result.scalar() or 0
    
    # 统计总收入（所有账户余额之和，需要转换为数值类型）
    revenue_result = await db.execute(select(func.sum(cast(Account.balance, Numeric))))
    total_revenue = revenue_result.scalar() or Decimal("0")
    
    # 按用户类型统计
    type_stats_result = await db.execute(
        select(User.user_type, func.count(User.id))
        .group_by(User.user_type)
    )
    type_stats = [
        {"type": row[0], "count": row[1]}
        for row in type_stats_result.fetchall()
    ]
    
    return BaseResponse(data={
        "total_users": total_users,
        "active_users": active_users,
        "total_repos": total_repos,
        "total_api_keys": total_api_keys,
        "total_revenue": float(total_revenue),
        "user_type_stats": type_stats,
    })


@router.get("/dashboard/recent-activity", response_model=BaseResponse[List[RecentActivity]])
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_super_admin_user),
):
    """
    获取最近活动
    
    返回最近的审计日志记录。
    """
    result = await db.execute(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    
    activities = [
        RecentActivity(
            id=str(log.id),
            action=log.action,
            username=log.username or "System",
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            description=log.description,
            ip_address=log.ip_address,
            status=log.status,
            created_at=log.created_at,
        )
        for log in logs
    ]
    
    return BaseResponse(data=activities)


# ==================== 用户管理接口 ====================

class UserListItem(BaseModel):
    """用户列表项"""
    id: str
    username: str
    email: str
    phone: Optional[str]
    user_type: str
    role: str
    user_status: str
    vip_level: int
    permissions: List[str]
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """更新用户请求模型"""
    user_type: Optional[str] = None
    role: Optional[str] = None
    user_status: Optional[str] = None
    vip_level: Optional[int] = None
    permissions: Optional[List[str]] = None


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: Optional[str] = Query(None, description="搜索关键词（用户名/邮箱）"),
    user_type: Optional[str] = Query(None, description="用户类型过滤"),
    user_status: Optional[str] = Query(None, description="状态过滤"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_super_admin_user),
):
    """
    获取用户列表
    
    支持分页、关键词搜索、用户类型和状态过滤。
    """
    # 构建查询条件
    conditions = []
    if keyword:
        conditions.append(
            or_(
                User.username.ilike(f"%{keyword}%"),
                User.email.ilike(f"%{keyword}%")
            )
        )
    if user_type:
        conditions.append(User.user_type == user_type)
    if user_status:
        conditions.append(User.user_status == user_status)
    
    # 查询总数
    count_query = select(func.count(User.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    offset = (page - 1) * page_size
    query = select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size)
    if conditions:
        query = query.where(and_(*conditions))
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    items = [
        UserListItem(
            id=str(user.id),
            username=user.username,
            email=user.email,
            phone=user.phone,
            user_type=user.user_type,
            role=user.role,
            user_status=user.user_status,
            vip_level=user.vip_level,
            permissions=user.permissions or [],
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
        for user in users
    ]
    
    # 返回扁平结构，与前端期望一致
    return BaseResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.put("/users/{user_id}", response_model=BaseResponse[UserListItem])
async def update_user(
    user_id: str,
    update_data: UserUpdateRequest = Body(..., description="用户更新数据"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_super_admin_user),
):
    """
    更新用户信息
    
    可更新用户类型、角色、状态、VIP等级和权限。
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 记录旧数据
    old_data = {
        "user_type": user.user_type,
        "role": user.role,
        "user_status": user.user_status,
        "vip_level": user.vip_level,
        "permissions": user.permissions,
    }
    
    # 更新字段
    if update_data.user_type is not None:
        user.user_type = update_data.user_type
    if update_data.role is not None:
        user.role = update_data.role
    if update_data.user_status is not None:
        user.user_status = update_data.user_status
    if update_data.vip_level is not None:
        user.vip_level = update_data.vip_level
    if update_data.permissions is not None:
        user.permissions = update_data.permissions
    
    # 记录审计日志
    audit_log = AuditLog(
        user_id=current_user["id"],
        username=current_user["username"],
        user_type=current_user["user_type"],
        action=AuditAction.USER_UPDATE,
        resource_type=ResourceType.USER,
        resource_id=str(user.id),
        description=f"更新用户 {user.username} 的信息",
        ip_address=None,
        old_data=old_data,
        new_data={
            "user_type": user.user_type,
            "role": user.role,
            "user_status": user.user_status,
            "vip_level": user.vip_level,
        },
        status="success",
    )
    db.add(audit_log)
    
    await db.commit()
    await db.refresh(user)
    
    return BaseResponse(data=UserListItem(
        id=str(user.id),
        username=user.username,
        email=user.email,
        phone=user.phone,
        user_type=user.user_type,
        role=user.role,
        user_status=user.user_status,
        vip_level=user.vip_level,
        permissions=user.permissions or [],
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    ))


@router.delete("/users/{user_id}", response_model=BaseResponse[dict])
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_super_admin_user),
):
    """
    删除用户
    
    软删除用户（将状态设置为 deleted）。
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if user.user_type == "super_admin":
        raise HTTPException(status_code=400, detail="不能删除超级管理员")
    
    # 软删除
    user.user_status = "deleted"
    
    # 记录审计日志
    audit_log = AuditLog(
        user_id=current_user["id"],
        username=current_user["username"],
        user_type=current_user["user_type"],
        action=AuditAction.USER_DELETE,
        resource_type=ResourceType.USER,
        resource_id=str(user.id),
        description=f"删除用户 {user.username}",
        status="success",
    )
    db.add(audit_log)
    
    await db.commit()
    
    return BaseResponse(message="用户已删除")


# ==================== 审计日志接口 ====================

class AuditLogItem(BaseModel):
    """审计日志项"""
    id: str
    user_id: Optional[str]
    username: Optional[str]
    user_type: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    description: Optional[str]
    ip_address: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: datetime


@router.get("/audit-logs")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    action: Optional[str] = Query(None, description="操作类型过滤"),
    resource_type: Optional[str] = Query(None, description="资源类型过滤"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_super_admin_user),
):
    """
    获取审计日志列表
    
    支持分页、各种过滤条件。
    """
    conditions = []
    if keyword:
        conditions.append(AuditLog.description.ilike(f"%{keyword}%"))
    if action:
        conditions.append(AuditLog.action == action)
    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)
    if start_date:
        conditions.append(AuditLog.created_at >= start_date)
    if end_date:
        conditions.append(AuditLog.created_at <= end_date)
    
    # 查询总数
    count_query = select(func.count(AuditLog.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    offset = (page - 1) * page_size
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)
    if conditions:
        query = query.where(and_(*conditions))
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    items = [
        AuditLogItem(
            id=str(log.id),
            user_id=str(log.user_id) if log.user_id else None,
            username=log.username,
            user_type=log.user_type,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            description=log.description,
            ip_address=log.ip_address,
            status=log.status,
            error_message=log.error_message,
            created_at=log.created_at,
        )
        for log in logs
    ]
    
    # 返回扁平结构，与前端期望一致
    return BaseResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


# ==================== 角色权限接口 ====================

class RoleItem(BaseModel):
    """角色项"""
    id: str
    name: str
    display_name: str
    description: Optional[str]
    permissions: List[str]
    is_system: bool
    is_active: bool
    priority: int
    user_count: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/roles", response_model=BaseResponse[List[RoleItem]])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_super_admin_user),
):
    """
    获取角色列表
    
    返回所有角色的详细信息和用户数量。
    """
    result = await db.execute(select(Role).order_by(Role.priority.desc()))
    roles = result.scalars().all()
    
    items = []
    for role in roles:
        # 统计该角色的用户数量
        count_result = await db.execute(
            select(func.count(User.id)).where(User.role == role.name)
        )
        user_count = count_result.scalar() or 0
        
        items.append(RoleItem(
            id=str(role.id),
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            permissions=role.permissions or [],
            is_system=role.is_system,
            is_active=role.is_active,
            priority=role.priority,
            user_count=user_count,
            created_at=role.created_at,
        ))
    
    return BaseResponse(data=items)


@router.get("/permissions", response_model=BaseResponse[dict])
async def get_permission_definitions(
    current_user: dict = Depends(get_current_super_admin_user),
):
    """
    获取权限定义列表
    
    返回所有权限的分组定义，用于前端展示。
    """
    from src.models.role import PERMISSION_DEFINITIONS
    return BaseResponse(data=PERMISSION_DEFINITIONS)


# ==================== 系统配置接口 ====================

class ConfigItem(BaseModel):
    """配置项"""
    id: str
    category: str
    key: str
    value: Optional[str]
    value_type: str
    label: Optional[str]
    description: Optional[str]
    options: List[str]
    is_system: bool
    is_visible: bool
    is_editable: bool
    updated_at: Optional[datetime]


@router.get("/configs", response_model=BaseResponse[List[dict]])
async def list_configs(
    category: Optional[str] = Query(None, description="配置分类过滤"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_super_admin_user),
):
    """
    获取系统配置列表
    
    返回所有系统配置项。
    """
    query = select(SystemConfig).order_by(SystemConfig.category, SystemConfig.key)
    if category:
        query = query.where(SystemConfig.category == category)
    
    result = await db.execute(query)
    configs = result.scalars().all()
    
    items = [
        {
            "id": str(config.id),
            "category": config.category,
            "key": config.key,
            "value": config.value,
            "value_type": config.value_type,
            "label": config.label,
            "description": config.description,
            "options": config.options or [],
            "is_system": config.is_system,
            "is_visible": config.is_visible,
            "is_editable": config.is_editable,
            "updated_at": config.updated_at,
        }
        for config in configs
    ]
    
    return BaseResponse(data=items)


class ConfigUpdateRequest(BaseModel):
    """更新配置请求模型"""
    value: str


@router.put("/configs/{config_id}", response_model=BaseResponse[dict])
async def update_config(
    config_id: str,
    update_data: ConfigUpdateRequest = Body(..., description="配置更新数据"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_super_admin_user),
):
    """
    更新系统配置
    
    更新指定配置项的值。
    """
    result = await db.execute(select(SystemConfig).where(SystemConfig.id == config_id))
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="配置项不存在")
    
    if not config.is_editable:
        raise HTTPException(status_code=400, detail="该配置项不可编辑")
    
    # 记录旧值
    old_value = config.value
    
    # 更新配置
    config.value = update_data.value
    config.updated_at = datetime.utcnow()
    config.updated_by = current_user["username"]
    
    # 记录审计日志
    audit_log = AuditLog(
        user_id=current_user["id"],
        username=current_user["username"],
        user_type=current_user["user_type"],
        action=AuditAction.SYSTEM_CONFIG_UPDATE,
        resource_type=ResourceType.SYSTEM,
        resource_id=str(config.id),
        description=f"更新系统配置 {config.key}",
        old_data={"value": old_value},
        new_data={"value": update_data.value},
        status="success",
    )
    db.add(audit_log)
    
    await db.commit()
    
    return BaseResponse(data={
        "id": str(config.id),
        "category": config.category,
        "key": config.key,
        "value": config.value,
        "updated_at": config.updated_at,
    })


@router.post("/configs/initialize", response_model=BaseResponse[dict])
async def initialize_configs(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_super_admin_user),
):
    """
    初始化系统配置
    
    将默认配置项添加到数据库（如果不存在）。
    """
    from src.models.system_config import DEFAULT_CONFIGS
    
    added_count = 0
    for key, config_def in DEFAULT_CONFIGS.items():
        category, name = key.split(".", 1)
        
        # 检查是否已存在
        result = await db.execute(
            select(SystemConfig).where(
                and_(
                    SystemConfig.category == category,
                    SystemConfig.key == name
                )
            )
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            config = SystemConfig(
                category=category,
                key=name,
                value=config_def.get("value", ""),
                value_type=config_def.get("type", "string"),
                label=config_def.get("label", name),
                options=config_def.get("options", []),
            )
            db.add(config)
            added_count += 1
    
    await db.commit()
    
    return BaseResponse(message=f"已添加 {added_count} 个配置项")
