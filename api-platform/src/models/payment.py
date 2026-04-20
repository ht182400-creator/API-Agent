"""Payment model - 支付模型"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Text, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.config.database import Base


class Payment(Base):
    """Payment model - 支付记录表"""
    
    __tablename__ = "payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Payment identifier
    payment_no = Column(String(50), unique=True, nullable=False)  # 支付单号
    order_no = Column(String(50), unique=True, nullable=False)  # 关联订单号
    
    # Payment type: recharge, purchase, refund
    payment_type = Column(String(20), nullable=False)
    
    # Amount
    amount = Column(String(20), nullable=False)  # 支付金额
    currency = Column(String(10), default="CNY")  # 货币类型
    
    # Package info (for recharge)
    package_id = Column(UUID(as_uuid=True), nullable=True)  # 充值套餐ID
    package_name = Column(String(100), nullable=True)  # 套餐名称
    
    # Payment method: alipay, wechat, paypal, bank_card
    payment_method = Column(String(20), nullable=True)
    
    # Payment channel: official, third_party
    payment_channel = Column(String(50), nullable=True)
    
    # Status: pending, processing, completed, failed, cancelled, refunded
    status = Column(String(20), default="pending", index=True)
    
    # Payment result
    transaction_id = Column(String(100), nullable=True)  # 第三方交易号
    payer_info = Column(Text, nullable=True)  # 支付人信息（JSON）
    pay_time = Column(DateTime, nullable=True)  # 支付完成时间
    
    # Callback info
    callback_url = Column(String(500), nullable=True)  # 回调通知地址
    callback_status = Column(String(20), default="pending")  # 回调状态
    callback_response = Column(Text, nullable=True)  # 回调响应
    callback_times = Column(BigInteger, default=0)  # 回调次数
    
    # Description
    description = Column(Text, nullable=True)
    remark = Column(Text, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment {self.payment_no}>"


class RechargePackage(Base):
    """Recharge package model - 充值套餐表"""
    
    __tablename__ = "recharge_packages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Package info
    name = Column(String(100), nullable=False)  # 套餐名称
    description = Column(Text, nullable=True)  # 套餐描述
    
    # Amount
    original_amount = Column(String(20), nullable=False)  # 原价
    price = Column(String(20), nullable=False)  # 现价
    discount = Column(String(10), nullable=True)  # 折扣率
    
    # Amount limits (for custom recharge)
    min_amount = Column(String(20), nullable=True)  # 最小充值金额
    max_amount = Column(String(20), nullable=True)  # 最大充值金额
    
    # Bonus
    bonus_amount = Column(String(20), default="0")  # 赠送金额
    bonus_ratio = Column(String(10), nullable=True)  # 赠送比例（如0.1表示10%）
    
    # Quota included
    included_calls = Column(BigInteger, nullable=True)  # 包含调用次数
    included_tokens = Column(BigInteger, nullable=True)  # 包含Token数
    
    # Validity
    validity_days = Column(BigInteger, nullable=True)  # 有效期（天）
    
    # Status
    is_active = Column(String(10), default="true")  # 是否启用
    is_featured = Column(String(10), default="false")  # 是否推荐
    sort_order = Column(BigInteger, default=0)  # 排序
    
    # Is custom amount package (true = 用户可自定义金额)
    is_custom = Column(String(10), default="false")  # 是否自定义金额套餐
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<RechargePackage {self.name}>"


class PaymentCallback(Base):
    """Payment callback model - 支付回调记录表"""
    
    __tablename__ = "payment_callbacks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Callback info
    callback_no = Column(String(50), unique=True, nullable=False)  # 回调单号
    channel = Column(String(20), nullable=False)  # 支付渠道
    
    # Request/Response
    request_body = Column(Text, nullable=True)  # 回调原始数据
    request_headers = Column(Text, nullable=True)  # 回调头信息
    response_body = Column(Text, nullable=True)  # 响应数据
    response_status = Column(BigInteger, nullable=True)  # 响应状态码
    
    # Processing result
    parse_result = Column(Text, nullable=True)  # 解析结果
    verify_result = Column(Text, nullable=True)  # 验签结果
    handle_result = Column(Text, nullable=True)  # 处理结果
    
    # Retry info
    retry_count = Column(BigInteger, default=0)  # 重试次数
    max_retries = Column(BigInteger, default=3)  # 最大重试次数
    next_retry_at = Column(DateTime, nullable=True)  # 下次重试时间
    
    # Status
    status = Column(String(20), default="pending")  # pending, success, failed
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    processed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<PaymentCallback {self.callback_no}>"
