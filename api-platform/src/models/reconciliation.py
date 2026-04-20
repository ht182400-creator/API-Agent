"""
平台账户模型

用于记录平台在各支付渠道的账户信息（仅用于对账系统）
"""
from sqlalchemy import Column, String, DECIMAL, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from src.config.database import Base


class PlatformAccount(Base):
    """平台账户表 - 记录平台在各支付渠道的账户"""
    
    __tablename__ = "platform_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 支付渠道: alipay/wechat/bankcard
    channel = Column(String(20), nullable=False, index=True, comment="支付渠道")
    
    # 账户类型: income(收入账户)/frozen(冻结账户)/available(可用账户)
    account_type = Column(String(20), nullable=False, default="income", comment="账户类型")
    
    # 第三方平台账户号
    account_no = Column(String(100), nullable=True, comment="第三方账户号")
    
    # 账户名称
    account_name = Column(String(100), nullable=True, comment="账户名称")
    
    # 账户余额
    balance = Column(DECIMAL(20, 2), default=0.00, comment="账户余额")
    
    # 币种
    currency = Column(String(10), default="CNY", comment="币种")
    
    # 账户状态
    status = Column(String(20), default="active", comment="状态: active/inactive")
    
    # 备注
    remark = Column(Text, nullable=True, comment="备注")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<PlatformAccount {self.channel} - {self.account_type}: {self.balance}>"


class ReconciliationRecord(Base):
    """对账记录表 - 记录每日对账结果"""
    
    __tablename__ = "reconciliation_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 对账日期
    reconcile_date = Column(DateTime(timezone=True), nullable=False, index=True, comment="对账日期")
    
    # 支付渠道
    channel = Column(String(20), nullable=False, index=True, comment="支付渠道")
    
    # 本地交易统计
    platform_trade_count = Column(String(20), default="0", comment="本地交易笔数")
    platform_trade_amount = Column(DECIMAL(20, 2), default=0.00, comment="本地交易金额")
    
    # 第三方交易统计
    channel_trade_count = Column(String(20), default="0", comment="第三方交易笔数")
    channel_trade_amount = Column(DECIMAL(20, 2), default=0.00, comment="第三方交易金额")
    
    # 匹配统计
    match_count = Column(String(20), default="0", comment="匹配笔数")
    match_amount = Column(DECIMAL(20, 2), default=0.00, comment="匹配金额")
    
    # 长款统计(本地多)
    long_count = Column(String(20), default="0", comment="长款笔数")
    long_amount = Column(DECIMAL(20, 2), default=0.00, comment="长款金额")
    
    # 短款统计(第三方多)
    short_count = Column(String(20), default="0", comment="短款笔数")
    short_amount = Column(DECIMAL(20, 2), default=0.00, comment="短款金额")
    
    # 金额不一致统计
    amount_diff_count = Column(String(20), default="0", comment="金额不一致笔数")
    amount_diff_total = Column(DECIMAL(20, 2), default=0.00, comment="金额差异总额")
    
    # 对账状态: pending/completed/disputed
    status = Column(String(20), default="pending", comment="对账状态")
    
    # 第三方账单文件路径
    bill_file_path = Column(String(500), nullable=True, comment="账单文件路径")
    
    # 账单文件内容(JSON格式存储)
    bill_content = Column(Text, nullable=True, comment="账单文件内容")
    
    # 完成时间
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="完成时间")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<ReconciliationRecord {self.reconcile_date} - {self.channel}: {self.status}>"


class ReconciliationDispute(Base):
    """对账差异明细表 - 记录对账中的差异项"""
    
    __tablename__ = "reconciliation_disputes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 对账记录ID
    reconciliation_id = Column(UUID(as_uuid=True), nullable=True, index=True, comment="对账记录ID")
    
    # 差异类型: long/short/amount_diff
    dispute_type = Column(String(20), nullable=False, comment="差异类型")
    
    # 本地订单号(长款时必填)
    local_order_no = Column(String(100), nullable=True, comment="本地订单号")
    
    # 第三方交易号(短款时必填)
    channel_trade_no = Column(String(100), nullable=True, comment="第三方交易号")
    
    # 金额
    local_amount = Column(DECIMAL(20, 2), nullable=True, comment="本地金额")
    channel_amount = Column(DECIMAL(20, 2), nullable=True, comment="第三方金额")
    diff_amount = Column(DECIMAL(20, 2), nullable=True, comment="差异金额")
    
    # 差异原因
    reason = Column(String(500), nullable=True, comment="差异原因")
    
    # 处理状态: pending/confirmed/resolved/ignored
    handle_status = Column(String(20), default="pending", comment="处理状态")
    
    # 处理备注
    handle_remark = Column(Text, nullable=True, comment="处理备注")
    
    # 处理人ID
    handler_id = Column(UUID(as_uuid=True), nullable=True, comment="处理人ID")
    
    # 处理时间
    handled_at = Column(DateTime(timezone=True), nullable=True, comment="处理时间")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<ReconciliationDispute {self.dispute_type}: {self.diff_amount}>"
