"""
通知模块数据库迁移脚本
用于创建通知表和初始化测试数据
"""

import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.config.database import SessionLocal, engine
from src.models.notification import Notification, NotificationPreference
from src.models import User


def create_notification_tables():
    """创建通知表"""
    from src.models.notification import Notification, NotificationPreference
    
    # 导入Base来创建表
    from src.config.database import Base
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("✅ 通知表创建成功")


def create_test_notifications(db: Session):
    """为所有用户创建测试通知"""
    
    # 获取所有用户
    users = db.query(User).filter(User.user_status == 'active').all()
    
    notification_templates = [
        # 系统通知
        {
            'title': '欢迎使用API服务平台',
            'content': '感谢您注册成为我们的用户。平台提供丰富的API接口供您使用，如有疑问请联系客服。',
            'notification_type': 'system',
            'priority': 'normal',
            'read': False,
        },
        {
            'title': '系统升级通知',
            'content': '平台将于本周日凌晨2:00-4:00进行系统升级，届时服务可能暂时不可用，请提前做好准备。',
            'notification_type': 'system',
            'priority': 'high',
            'read': False,
        },
        # 账单通知
        {
            'title': '账单已生成',
            'content': '您2026年4月的账单已生成，当前应支付金额为 ¥128.50，请及时支付以保持服务正常运行。',
            'notification_type': 'billing',
            'priority': 'high',
            'read': False,
        },
        {
            'title': '配额使用提醒',
            'content': '您的API配额已使用80%，剩余配额约可支持3天使用。建议您及时充值以避免服务中断。',
            'notification_type': 'billing',
            'priority': 'high',
            'read': True,
        },
        # API通知
        {
            'title': 'API Key创建成功',
            'content': '您的新API Key已成功创建。请妥善保管，不要在公开场合泄露您的密钥。',
            'notification_type': 'api',
            'priority': 'normal',
            'read': True,
        },
        {
            'title': 'API调用异常提醒',
            'content': '检测到您的API在过去1小时内有较高错误率(>5%)，请检查您的调用代码或密钥配置。',
            'notification_type': 'api',
            'priority': 'high',
            'read': False,
        },
        # 安全通知
        {
            'title': '异地登录提醒',
            'content': '检测到您的账号在新的IP地址登录。如果这不是您本人的操作，请立即修改密码并联系客服。',
            'notification_type': 'security',
            'priority': 'urgent',
            'read': False,
        },
    ]
    
    count = 0
    for user in users:
        # 为每个用户创建几条通知
        for i, template in enumerate(notification_templates):
            notification = Notification(
                id=uuid.uuid4(),
                user_id=user.id,
                title=template['title'],
                content=template['content'],
                notification_type=template['notification_type'],
                priority=template['priority'],
                status='read' if template['read'] else 'unread',
                read_at=datetime.utcnow() - timedelta(days=2) if template['read'] else None,
                created_at=datetime.utcnow() - timedelta(hours=i * 3),
            )
            db.add(notification)
            count += 1
        
        # 创建通知偏好设置
        preference = NotificationPreference(
            id=uuid.uuid4(),
            user_id=user.id,
            email_enabled=True,
            in_app_enabled=True,
            push_enabled=False,
            preferences={
                'system': True,
                'billing': True,
                'api': True,
                'security': True,
            },
        )
        db.add(preference)
    
    db.commit()
    print(f"✅ 已为 {len(users)} 个用户创建 {count} 条测试通知")


def run_migration():
    """运行迁移"""
    print("🚀 开始通知模块数据迁移...")
    
    # 创建表
    create_notification_tables()
    
    # 创建测试数据
    db = SessionLocal()
    try:
        # 检查是否已有通知数据
        existing = db.query(Notification).first()
        if existing:
            print("ℹ️  通知数据已存在，跳过测试数据创建")
        else:
            create_test_notifications(db)
    finally:
        db.close()
    
    print("✨ 迁移完成!")


if __name__ == '__main__':
    run_migration()
