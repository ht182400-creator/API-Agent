"""API Key model - API Key模型"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Integer, Boolean, DateTime, BigInteger, ARRAY, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import relationship

from src.config.database import Base


class APIKey(Base):
    """API Key model - API Key表"""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Key information
    key_name = Column(String(100), nullable=False)
    key_prefix = Column(String(20), nullable=False, index=True)  # sk_test_xxxxx
    key_hash = Column(String(64), nullable=False, unique=True)  # SHA256 hash
    secret_hash = Column(String(128), nullable=True)  # HMAC secret hash
    encrypted_key = Column(Text, nullable=True)  # 加密存储的原始 key，用于查看

    # Authentication configuration
    auth_type = Column(String(20), default="api_key")  # api_key, hmac, jwt
    allowed_ips = Column(ARRAY(String), nullable=True)  # IP whitelist
    allowed_repos = Column(ARRAY(UUID), nullable=True)  # Allowed repositories
    denied_repos = Column(ARRAY(UUID), nullable=True)  # Denied repositories

    # Rate limiting configuration
    rate_limit_rpm = Column(Integer, default=1000)  # Requests per minute
    rate_limit_rph = Column(Integer, default=10000)  # Requests per hour
    daily_quota = Column(BigInteger, nullable=True)  # Daily quota (NULL = unlimited)
    monthly_quota = Column(BigInteger, nullable=True)  # Monthly quota (NULL = unlimited)
    is_balance_enabled = Column(Boolean, default=False)  # 是否启用余额扣费

    # Status
    status = Column(String(20), default="active")  # active, disabled, expired

    # Expiration
    expires_at = Column(DateTime, nullable=True)  # NULL = never expires

    # Statistics
    total_calls = Column(BigInteger, default=0)
    last_call_at = Column(DateTime, nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    disabled_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")
    usage_logs = relationship("KeyUsageLog", back_populates="api_key")

    def __repr__(self):
        return f"<APIKey {self.key_prefix}***>"

    def is_active(self) -> bool:
        """Check if key is active and not expired"""
        if self.status != "active":
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True


class KeyUsageLog(Base):
    """Key usage log model - Key使用记录表"""

    __tablename__ = "key_usage_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)

    # Call information
    repo_id = Column(UUID(as_uuid=True), nullable=True)
    endpoint = Column(String(255), nullable=True)
    method = Column(String(10), nullable=True)
    status_code = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)

    # Billing information
    tokens_used = Column(Integer, nullable=True)
    cost = Column(String(10), nullable=True)

    # Request information
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Time
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    api_key = relationship("APIKey", back_populates="usage_logs")

    def __repr__(self):
        return f"<KeyUsageLog {self.id}>"
