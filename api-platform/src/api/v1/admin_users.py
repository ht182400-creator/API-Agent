"""Admin Users API - 管理员用户管理接口"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.user import User
from src.models.audit_log import AuditLog, AuditAction, ResourceType
from src.schemas.response import BaseResponse
from src.services.auth_service import get_current_admin_user

router = APIRouter(tags=["管理员"])


# ==================== 请求/响应模型 ====================

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
    """更新用户请求模型（管理员限制版）"""
    user_status: Optional[str] = None  # 管理员只能修改状态
    vip_level: Optional[int] = None


class UserListResponse(BaseModel):
    """用户列表响应"""
    items: List[UserListItem]
    total: int
    page: int
    page_size: int


# ==================== 用户管理接口 ====================

@router.get("/users", response_model=BaseResponse[UserListResponse])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: Optional[str] = Query(None, description="搜索关键词（用户名/邮箱）"),
    user_type: Optional[str] = Query(None, description="用户类型过滤"),
    user_status: Optional[str] = Query(None, description="状态过滤"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    获取用户列表（管理员版本）
    
    管理员可以查看所有用户，但只能管理非管理员用户。
    """
    # 构建查询条件 - 排除超级管理员
    conditions = [User.user_type != "super_admin"]
    
    if keyword:
        conditions.append(
            or_(
                User.username.ilike(f"%{keyword}%"),
                User.email.ilike(f"%{keyword}%"),
            )
        )
    
    if user_type:
        # 管理员不能查看超级管理员
        if user_type == "super_admin":
            pass  # 返回空结果
        else:
            conditions.append(User.user_type == user_type)
    
    if user_status:
        conditions.append(User.user_status == user_status)
    
    # 查询总数
    count_query = select(func.count(User.id)).where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    offset = (page - 1) * page_size
    query = (
        select(User)
        .where(and_(*conditions))
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    users = result.scalars().all()
    
    # 转换为响应格式
    items = [
        UserListItem(
            id=str(user.id),
            username=user.username,
            email=user.email,
            phone=user.phone,
            user_type=user.user_type,
            role=user.role,
            user_status=user.user_status,
            vip_level=user.vip_level or 0,
            permissions=user.permissions or [],
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
        for user in users
    ]
    
    return BaseResponse(data=UserListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    ))


@router.put("/users/{user_id}", response_model=BaseResponse[UserListItem])
async def update_user(
    user_id: str,
    update_data: UserUpdateRequest = Body(..., description="用户更新数据"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    更新用户信息（管理员版本）
    
    管理员只能修改用户状态和VIP等级，不能修改管理员或超级管理员。
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 管理员不能修改其他管理员或超级管理员
    if user.user_type in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=403, 
            detail="无权修改管理员或超级管理员的账户"
        )
    
    # 记录旧数据
    old_data = {
        "user_status": user.user_status,
        "vip_level": user.vip_level,
    }
    
    # 更新字段
    if update_data.user_status is not None:
        user.user_status = update_data.user_status
    if update_data.vip_level is not None:
        user.vip_level = update_data.vip_level
    
    # 记录审计日志
    audit_log = AuditLog(
        user_id=current_user["id"],
        username=current_user["username"],
        user_type=current_user["user_type"],
        action=AuditAction.USER_UPDATE,
        resource_type=ResourceType.USER,
        resource_id=str(user.id),
        description=f"管理员更新用户 {user.username} 的信息",
        ip_address=None,
        old_data=old_data,
        new_data={
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
        vip_level=user.vip_level or 0,
        permissions=user.permissions or [],
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    ))


@router.delete("/users/{user_id}", response_model=BaseResponse[dict])
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    删除用户（管理员版本）
    
    管理员只能删除普通用户、仓库所有者和开发者，不能删除管理员或超级管理员。
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 管理员不能删除其他管理员或超级管理员
    if user.user_type in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=403,
            detail="无权删除管理员或超级管理员账户"
        )
    
    # 不能删除自己
    if user.id == current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="不能删除自己的账户"
        )
    
    # 记录审计日志
    audit_log = AuditLog(
        user_id=current_user["id"],
        username=current_user["username"],
        user_type=current_user["user_type"],
        action=AuditAction.USER_DELETE,
        resource_type=ResourceType.USER,
        resource_id=str(user.id),
        description=f"管理员删除用户 {user.username}",
        ip_address=None,
        old_data={"username": user.username, "email": user.email},
        new_data=None,
        status="success",
    )
    db.add(audit_log)
    
    # 删除用户（级联删除关联数据）
    await db.delete(user)
    await db.commit()
    
    return BaseResponse(data={"id": user_id}, message="用户已删除")
