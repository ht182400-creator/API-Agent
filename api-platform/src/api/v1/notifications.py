"""Notification API - 通知接口"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.config.database import get_db
from src.services.auth_service import get_current_user
from src.models.user import User
from src.services.notification_service import NotificationService

router = APIRouter(tags=["通知"])
security = HTTPBearer()


# ============== Pydantic Schemas ==============

class NotificationCreate(BaseModel):
    """创建通知请求"""
    title: str
    content: str
    notification_type: str = "system"
    priority: str = "normal"


class NotificationResponse(BaseModel):
    """通知响应"""
    id: str
    title: str
    content: str
    notification_type: str
    priority: str
    status: str
    extra_data: dict
    created_at: str
    read_at: Optional[str] = None


class NotificationListResponse(BaseModel):
    """通知列表响应"""
    total: int
    page: int
    page_size: int
    notifications: list


class NotificationPreferenceUpdate(BaseModel):
    """通知偏好更新"""
    email_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    preferences: Optional[dict] = None


class NotificationPreferenceResponse(BaseModel):
    """通知偏好响应"""
    email_enabled: bool
    in_app_enabled: bool
    push_enabled: bool
    preferences: dict


class UnreadCountResponse(BaseModel):
    """未读数量响应"""
    unread_count: int


# ============== API Endpoints ==============

@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    status: Optional[str] = Query(None, description="通知状态：unread/read"),
    notification_type: Optional[str] = Query(None, description="通知类型：system/billing/api/security"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取通知列表"""
    result = await NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        status=status,
        notification_type=notification_type,
        page=page,
        page_size=page_size,
    )
    
    return {
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "notifications": [
            {
                "id": str(n.id),
                "title": n.title,
                "content": n.content,
                "notification_type": n.notification_type,
                "priority": n.priority,
                "status": n.status,
                "extra_data": n.extra_data or {},
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "read_at": n.read_at.isoformat() if n.read_at else None,
            }
            for n in result["notifications"]
        ],
    }


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取未读通知数量"""
    count = await NotificationService.get_unread_count(db, current_user.id)
    return {"unread_count": count}


@router.get("/recent", response_model=list)
async def get_recent_notifications(
    limit: int = Query(5, ge=1, le=20, description="数量限制"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取最近未读通知（用于下拉面板）"""
    notifications = await NotificationService.get_recent_notifications(
        db=db,
        user_id=current_user.id,
        limit=limit,
    )
    
    return [
        {
            "id": str(n.id),
            "title": n.title,
            "content": n.content,
            "notification_type": n.notification_type,
            "priority": n.priority,
            "status": n.status,
            "extra_data": n.extra_data or {},
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "read_at": n.read_at.isoformat() if n.read_at else None,
        }
        for n in notifications
    ]


@router.post("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记单条通知为已读"""
    try:
        nid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的通知ID")
    
    notification = await NotificationService.mark_as_read(db, nid, current_user.id)
    
    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")
    
    return {"success": True, "message": "标记已读成功"}


@router.post("/read-all")
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记所有通知为已读"""
    count = await NotificationService.mark_all_as_read(db, current_user.id)
    return {"success": True, "message": f"已标记 {count} 条通知为已读"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除通知"""
    try:
        nid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的通知ID")
    
    success = await NotificationService.delete_notification(db, nid, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="通知不存在")
    
    return {"success": True, "message": "删除成功"}


@router.delete("/read/delete-all")
async def delete_all_read_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除所有已读通知"""
    count = await NotificationService.delete_all_read(db, current_user.id)
    return {"success": True, "message": f"已删除 {count} 条已读通知"}


# ============== 通知偏好设置 ==============

@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_notification_preference(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取通知偏好设置"""
    preference = await NotificationService.get_notification_preference(db, current_user.id)
    
    return {
        "email_enabled": preference.email_enabled,
        "in_app_enabled": preference.in_app_enabled,
        "push_enabled": preference.push_enabled,
        "preferences": preference.preferences or {},
    }


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_notification_preference(
    update_data: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新通知偏好设置"""
    preferences = update_data.model_dump(exclude_none=True)
    
    preference = await NotificationService.update_notification_preference(
        db=db,
        user_id=current_user.id,
        preferences=preferences,
    )
    
    return {
        "email_enabled": preference.email_enabled,
        "in_app_enabled": preference.in_app_enabled,
        "push_enabled": preference.push_enabled,
        "preferences": preference.preferences or {},
    }


# ============== 管理员接口 ==============

@router.post("", response_model=NotificationResponse)
async def create_notification_for_user(
    notification_data: NotificationCreate,
    user_id: str = Query(..., description="目标用户ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建通知（管理员接口）"""
    # 只有管理员才能创建通知
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的用户ID")
    
    notification = await NotificationService.create_notification(
        db=db,
        user_id=target_user_id,
        title=notification_data.title,
        content=notification_data.content,
        notification_type=notification_data.notification_type,
        priority=notification_data.priority,
    )
    
    return {
        "id": str(notification.id),
        "title": notification.title,
        "content": notification.content,
        "notification_type": notification.notification_type,
        "priority": notification.priority,
        "status": notification.status,
        "extra_data": notification.extra_data or {},
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
        "read_at": None,
    }


@router.post("/broadcast")
async def broadcast_notification(
    notification_data: NotificationCreate,
    user_type: Optional[str] = Query(None, description="用户类型筛选"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """广播通知给所有用户或指定类型用户（管理员接口）"""
    # 只有管理员才能广播通知
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    from src.models.user import User as UserModel
    
    query = select(UserModel.id)
    if user_type:
        query = query.where(UserModel.user_type == user_type)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    count = 0
    for user_id in users:
        await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            title=notification_data.title,
            content=notification_data.content,
            notification_type=notification_data.notification_type,
            priority=notification_data.priority,
        )
        count += 1
    
    return {"success": True, "message": f"已向 {count} 个用户发送通知"}
