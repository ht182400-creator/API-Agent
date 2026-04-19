"""Billing model - 计费模型"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Text, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.config.database import Base


class Account(Base):
    """Account model - 账户表"""

    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Account type: balance, bonus, voucher
    account_type = Column(String(20), nullable=False)

    # Balance
    balance = Column(String(20), default="0")
    frozen_balance = Column(String(20), default="0")  # Frozen amount

    # Statistics
    total_recharge = Column(String(20), default="0")  # Total recharge
    total_consume = Column(String(20), default="0")  # Total consumption

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="accounts")

    def __repr__(self):
        return f"<Account {self.user_id}:{self.account_type}>"


class Bill(Base):
    """Bill model - 账单表"""

    __tablename__ = "bills"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Bill identifier
    bill_no = Column(String(50), unique=True, nullable=False)
    bill_type = Column(String(20), nullable=False)  # recharge, consume, refund, bonus

    # Amount
    amount = Column(String(20), nullable=False)  # Change amount (positive or negative)
    balance_before = Column(String(20), nullable=False)
    balance_after = Column(String(20), nullable=False)

    # Source
    source_type = Column(String(20), nullable=True)  # api_call, refund, admin, manual
    source_id = Column(String(50), nullable=True)  # Related call record ID

    # Description
    description = Column(Text, nullable=True)
    remark = Column(Text, nullable=True)

    # Status: pending, completed, failed, cancelled
    status = Column(String(20), default="completed")

    # Payment information
    payment_method = Column(String(20), nullable=True)
    payment_channel = Column(String(50), nullable=True)
    transaction_id = Column(String(100), nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="bills")

    def __repr__(self):
        return f"<Bill {self.bill_no}>"


class Quota(Base):
    """Quota model - 配额表"""

    __tablename__ = "quotas"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    key_id = Column(UUID(as_uuid=True), nullable=True)
    repo_id = Column(UUID(as_uuid=True), nullable=True)

    # Quota type: rpm, rph, daily, monthly
    quota_type = Column(String(20), nullable=False)

    # Quota limit
    quota_limit = Column(BigInteger, nullable=False)
    quota_used = Column(BigInteger, default=0)
    quota_remaining = Column(BigInteger, nullable=True)

    # Reset cycle: never, hourly, daily, monthly
    reset_type = Column(String(20), nullable=False)
    reset_at = Column(DateTime, nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Quota {self.quota_type}:{self.quota_used}/{self.quota_limit}>"

    @property
    def remaining(self) -> int:
        """Calculate remaining quota"""
        remaining = self.quota_limit - self.quota_used
        return max(0, remaining)

    def is_exceeded(self) -> bool:
        """Check if quota is exceeded"""
        return self.quota_used >= self.quota_limit


class APICallLog(Base):
    """API Call Log model - API调用日志表"""

    __tablename__ = "api_call_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign keys
    repo_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Request information
    endpoint = Column(String(255), nullable=True)
    method = Column(String(10), nullable=True)
    request_path = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)

    # Response information
    status_code = Column(BigInteger, nullable=True)
    response_time = Column(String(20), nullable=True)  # ms

    # Usage information
    tokens_used = Column(BigInteger, default=0)
    cost = Column(String(20), default="0")

    # Source/Client information
    source = Column(String(50), nullable=True)  # web, ios, android, api
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Error information
    error_message = Column(Text, nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<APICallLog {self.id}:{self.endpoint}>"
