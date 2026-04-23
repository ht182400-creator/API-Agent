"""Notification service - 通知服务（异步版本）"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import and_, select, func, update, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.models.notification import Notification, NotificationPreference
from src.config.logging_config import get_logger

logger = get_logger("notification")


class NotificationService:
    """通知服务类"""

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str,
        content: str,
        notification_type: str = "system",
        priority: str = "normal",
        extra_data: Optional[Dict[str, Any]] = None,
        expire_at: Optional[datetime] = None,
    ) -> Notification:
        """创建通知"""
        notification = Notification(
            user_id=user_id,
            title=title,
            content=content,
            notification_type=notification_type,
            priority=priority,
            extra_data=extra_data or {},
            expire_at=expire_at,
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        notification_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """获取用户通知列表"""
        # 构建基础条件
        conditions = [
            Notification.user_id == user_id,
            Notification.is_deleted == False,
        ]
        
        if status:
            conditions.append(Notification.status == status)
        
        if notification_type:
            conditions.append(Notification.notification_type == notification_type)

        # 统计总数
        count_query = select(func.count(Notification.id)).where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页查询
        query = (
            select(Notification)
            .where(and_(*conditions))
            .order_by(desc(Notification.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        notifications = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "notifications": notifications,
        }

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
        """获取未读通知数量"""
        query = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.status == "unread",
                Notification.is_deleted == False,
            )
        )
        result = await db.execute(query)
        return result.scalar() or 0

    @staticmethod
    async def mark_as_read(db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Notification]:
        """标记单条通知为已读"""
        query = select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        result = await db.execute(query)
        notification = result.scalar_one_or_none()
        
        if notification and notification.status == "unread":
            notification.status = "read"
            notification.read_at = datetime.utcnow()
            await db.commit()
            await db.refresh(notification)
        
        return notification

    @staticmethod
    async def mark_all_as_read(db: AsyncSession, user_id: uuid.UUID) -> int:
        """标记所有通知为已读，返回已读数量"""
        now = datetime.utcnow()
        query = (
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.status == "unread",
                    Notification.is_deleted == False,
                )
            )
            .values(status="read", read_at=now)
        )
        result = await db.execute(query)
        await db.commit()
        return result.rowcount or 0

    @staticmethod
    async def delete_notification(db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """删除通知（软删除）"""
        query = select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        result = await db.execute(query)
        notification = result.scalar_one_or_none()
        
        if notification:
            notification.is_deleted = True
            await db.commit()
            return True
        return False

    @staticmethod
    async def delete_all_read(db: AsyncSession, user_id: uuid.UUID) -> int:
        """删除所有已读通知"""
        query = (
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.status == "read",
                    Notification.is_deleted == False,
                )
            )
            .values(is_deleted=True)
        )
        result = await db.execute(query)
        await db.commit()
        return result.rowcount or 0

    @staticmethod
    async def get_notification_preference(db: AsyncSession, user_id: uuid.UUID) -> NotificationPreference:
        """获取用户通知偏好"""
        query = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id
        )
        result = await db.execute(query)
        # 安全处理：使用 scalars().all() 检查多记录情况
        preferences = result.scalars().all()
        if len(preferences) > 1:
            logger.warning(f"[Notification] Multiple preferences found for user {user_id}, using first one")
            preference = preferences[0]
        elif len(preferences) == 0:
            preference = None
        else:
            preference = preferences[0]
        
        if not preference:
            preference = NotificationPreference(user_id=user_id)
            db.add(preference)
            await db.commit()
            await db.refresh(preference)
        
        return preference

    @staticmethod
    async def update_notification_preference(
        db: AsyncSession,
        user_id: uuid.UUID,
        preferences: Dict[str, Any],
    ) -> NotificationPreference:
        """更新用户通知偏好"""
        preference = await NotificationService.get_notification_preference(db, user_id)
        
        if "email_enabled" in preferences:
            preference.email_enabled = preferences["email_enabled"]
        if "in_app_enabled" in preferences:
            preference.in_app_enabled = preferences["in_app_enabled"]
        if "push_enabled" in preferences:
            preference.push_enabled = preferences["push_enabled"]
        if "preferences" in preferences:
            preference.preferences = preferences["preferences"]
        
        await db.commit()
        await db.refresh(preference)
        return preference

    @staticmethod
    async def get_recent_notifications(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 5,
    ) -> List[Notification]:
        """获取最近的未读通知（用于下拉面板）"""
        query = (
            select(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.status == "unread",
                    Notification.is_deleted == False,
                )
            )
            .order_by(desc(Notification.created_at))
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create_system_notification(
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str,
        content: str,
        priority: str = "normal",
    ) -> Notification:
        """创建系统通知"""
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            title=title,
            content=content,
            notification_type="system",
            priority=priority,
        )

    @staticmethod
    async def create_billing_notification(
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str,
        content: str,
        priority: str = "high",
    ) -> Notification:
        """创建账单通知"""
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            title=title,
            content=content,
            notification_type="billing",
            priority=priority,
        )

    @staticmethod
    async def create_security_notification(
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str,
        content: str,
    ) -> Notification:
        """创建安全通知（高优先级）"""
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            title=title,
            content=content,
            notification_type="security",
            priority="high",
        )
