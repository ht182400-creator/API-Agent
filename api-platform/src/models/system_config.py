"""System Config model - 系统配置模型"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.config.database import Base


class SystemConfig(Base):
    """System Config model - 系统配置表"""

    __tablename__ = "system_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 配置分类和键
    category = Column(String(50), nullable=False, index=True)  # general, security, database, logging, api, email, etc.
    key = Column(String(100), nullable=False, index=True)
    
    # 配置值
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default="string")  # string, number, boolean, json
    is_encrypted = Column(Boolean, default=False)  # 是否加密存储
    
    # 配置描述
    label = Column(String(200), nullable=True)  # 中文显示名称
    description = Column(Text, nullable=True)  # 配置说明
    options = Column(JSONB, default=list)  # 可选值列表（用于下拉选择）
    
    # 状态
    is_system = Column(Boolean, default=False)  # 是否系统级配置（不可删除）
    is_visible = Column(Boolean, default=True)  # 是否在前端显示
    is_editable = Column(Boolean, default=True)  # 是否可编辑
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(100), nullable=True)

    # 复合唯一索引
    __table_args__ = (
        # 使用 String 作为唯一约束 (PostgreSQL 特定)
    )

    def __repr__(self):
        return f"<SystemConfig {self.category}.{self.key}>"


# 配置分类常量
class ConfigCategory:
    """配置分类常量"""
    GENERAL = "general"  # 通用设置
    SECURITY = "security"  # 安全设置
    DATABASE = "database"  # 数据库设置
    API = "api"  # API设置
    EMAIL = "email"  # 邮件设置
    SMS = "sms"  # 短信设置
    PAYMENT = "payment"  # 支付设置
    LOGGING = "logging"  # 日志设置
    CACHE = "cache"  # 缓存设置
    RATE_LIMIT = "rate_limit"  # 限流设置


# 默认配置项
DEFAULT_CONFIGS = {
    # 通用设置
    "general.site_name": {"value": "API Platform", "type": "string", "label": "平台名称"},
    "general.site_url": {"value": "https://api.example.com", "type": "string", "label": "平台地址"},
    "general.support_email": {"value": "support@example.com", "type": "string", "label": "支持邮箱"},
    "general.timezone": {"value": "Asia/Shanghai", "type": "string", "label": "时区"},
    "general.language": {"value": "zh-CN", "type": "string", "label": "默认语言"},
    
    # 安全设置
    "security.password_min_length": {"value": "8", "type": "number", "label": "密码最小长度"},
    "security.password_require_uppercase": {"value": "true", "type": "boolean", "label": "必须包含大写字母"},
    "security.password_require_number": {"value": "true", "type": "boolean", "label": "必须包含数字"},
    "security.password_require_special": {"value": "true", "type": "boolean", "label": "必须包含特殊字符"},
    "security.session_timeout": {"value": "30", "type": "number", "label": "会话超时时间(分钟)"},
    "security.max_login_attempts": {"value": "5", "type": "number", "label": "最大登录失败次数"},
    "security.enable_mfa": {"value": "false", "type": "boolean", "label": "启用双因素认证"},
    "security.enable_captcha": {"value": "true", "type": "boolean", "label": "启用验证码"},
    
    # API设置
    "api.default_rate_limit_rpm": {"value": "60", "type": "number", "label": "默认API限流(RPM)"},
    "api.default_daily_quota": {"value": "1000", "type": "number", "label": "默认每日配额"},
    "api.key_prefix": {"value": "sk", "type": "string", "label": "API Key前缀"},
    "api.key_length": {"value": "32", "type": "number", "label": "API Key长度"},
    
    # 日志设置
    "logging.level": {"value": "INFO", "type": "string", "label": "日志级别", 
                     "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
    "logging.retention_days": {"value": "30", "type": "number", "label": "日志保留天数"},
    "logging.enable_audit": {"value": "true", "type": "boolean", "label": "启用审计日志"},
    "logging.enable_metrics": {"value": "true", "type": "boolean", "label": "启用性能指标"},
    
    # 缓存设置
    "cache.type": {"value": "memory", "type": "string", "label": "缓存类型",
                   "options": ["redis", "memcached", "memory"]},
    "cache.ttl": {"value": "3600", "type": "number", "label": "缓存TTL(秒)"},
    
    # 限流设置
    "rate_limit.enabled": {"value": "true", "type": "boolean", "label": "启用限流"},
    "rate_limit.default_rpm": {"value": "60", "type": "number", "label": "默认RPM"},
    "rate_limit.default_rph": {"value": "1000", "type": "number", "label": "默认RPH"},

    # 支付设置 - 模拟模式
    "payment.mock_mode": {"value": "true", "type": "boolean", "label": "支付模式", 
                         "description": "true=模拟模式(测试用), false=真实支付",
                         "options": ["true", "false"]},
    "payment.mock_pay_url": {"value": "/mock-payment", "type": "string", "label": "模拟支付页面地址"},

    # 支付设置 - 支付宝
    "payment.alipay.enabled": {"value": "false", "type": "boolean", "label": "启用支付宝"},
    "payment.alipay.app_id": {"value": "", "type": "string", "label": "支付宝AppID", "encrypted": True},
    "payment.alipay.private_key": {"value": "", "type": "string", "label": "应用私钥(RSA2)", "encrypted": True},
    "payment.alipay.alipay_public_key": {"value": "", "type": "string", "label": "支付宝公钥", "encrypted": True},
    "payment.alipay.notify_url": {"value": "", "type": "string", "label": "异步通知地址"},
    "payment.alipay.return_url": {"value": "", "type": "string", "label": "同步跳转地址"},
    "payment.alipay.sandbox": {"value": "true", "type": "boolean", "label": "沙箱环境"},

    # 支付设置 - 微信支付
    "payment.wechat.enabled": {"value": "false", "type": "boolean", "label": "启用微信支付"},
    "payment.wechat.mchid": {"value": "", "type": "string", "label": "微信商户号", "encrypted": True},
    "payment.wechat.appid": {"value": "", "type": "string", "label": "微信AppID", "encrypted": True},
    "payment.wechat.api_key": {"value": "", "type": "string", "label": "微信API密钥", "encrypted": True},
    "payment.wechat.cert_path": {"value": "", "type": "string", "label": "SSL证书路径", "encrypted": True},
    "payment.wechat.notify_url": {"value": "", "type": "string", "label": "支付结果通知地址"},
    "payment.wechat.sandbox": {"value": "true", "type": "boolean", "label": "沙箱环境"},

    # 支付设置 - 银行卡
    "payment.bankcard.enabled": {"value": "false", "type": "boolean", "label": "启用银行卡支付"},
    "payment.bankcard.merchant_id": {"value": "", "type": "string", "label": "商户号", "encrypted": True},
    "payment.bankcard.terminal_id": {"value": "", "type": "string", "label": "终端号", "encrypted": True},
    "payment.bankcard.notify_url": {"value": "", "type": "string", "label": "支付结果通知地址"},
}
