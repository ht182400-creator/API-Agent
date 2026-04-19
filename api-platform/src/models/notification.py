"""Notification model - 通知模型"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.config.database import Base


class Notification(Base):
    """Notification model - 通知表"""

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 接收通知的用户ID
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # 通知类型：system（系统通知）、billing（账单通知）、api（API通知）、security（安全通知）
    notification_type = Column(String(30), nullable=False, default="system")
    
    # 通知标题
    title = Column(String(200), nullable=False)
    
    # 通知内容
    content = Column(Text, nullable=False)
    
    # 额外数据（JSON格式，如跳转链接、关联ID等）
    extra_data = Column(JSONB, default=dict)
    
    # 通知状态：unread（未读）、read（已读）、deleted（已删除）
    status = Column(String(20), nullable=False, default="unread")
    
    # 是否已删除
    is_deleted = Column(Boolean, default=False)
    
    # 优先级：low（低）、normal（普通）、high（高）、urgent（紧急）
    priority = Column(String(20), nullable=False, default="normal")
    
    # 过期时间（可选，过期后自动标记为已过期）
    expire_at = Column(DateTime, nullable=True)
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)  # 阅读时间

    def __repr__(self):
        return f"<Notification {self.title}>"


class NotificationPreference(Base):
    """Notification preference model - 用户通知偏好设置"""

    __tablename__ = "notification_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    # 是否启用邮件通知
    email_enabled = Column(Boolean, default=True)
    
    # 是否启用站内通知
    in_app_enabled = Column(Boolean, default=True)
    
    # 是否启用推送通知
    push_enabled = Column(Boolean, default=False)
    
    # 通知类型偏好
    preferences = Column(JSONB, default={
        "system": True,
        "billing": True,
        "api": True,
        "security": True,
    })

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<NotificationPreference user_id={self.user_id}>"
