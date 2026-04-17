"""Repository model - 仓库模型"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.config.database import Base


class Repository(Base):
    """Repository model - 仓库表"""

    __tablename__ = "repositories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Owner information
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_type = Column(String(20), nullable=False)  # internal, external

    # Basic information
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, index=True)  # URL-friendly name
    display_name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)

    # Repository type
    repo_type = Column(String(50), nullable=False, index=True)  # psychology, stock, ai, translation
    protocol = Column(String(20), nullable=False)  # http, grpc, websocket
    adapter_id = Column(String(50), nullable=True)  # Adapter ID

    # Access information
    endpoint_url = Column(String(500), nullable=True)  # Repository API address
    health_check_url = Column(String(500), nullable=True)  # Health check address
    api_docs_url = Column(String(500), nullable=True)  # API docs address

    # Configuration
    config = Column(JSONB, default=dict)

    # Status: pending, approved, rejected, online, offline
    status = Column(String(20), default="pending", index=True)
    rejection_reason = Column(Text, nullable=True)

    # SLA configuration
    sla_uptime = Column(String(10), nullable=True)  # SLA availability target
    sla_latency_p99 = Column(Integer, nullable=True)  # SLA P99 latency target (ms)

    # Statistics
    total_calls = Column(BigInteger, default=0)
    active_keys = Column(Integer, default=0)
    avg_latency_ms = Column(Integer, nullable=True)
    success_rate = Column(String(10), nullable=True)

    # Review information
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), nullable=True)

    # Online information
    online_at = Column(DateTime, nullable=True)
    offline_at = Column(DateTime, nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="repositories")
    pricing = relationship("RepoPricing", back_populates="repository", uselist=False)
    configs = relationship("RepoConfig", back_populates="repository")
    stats = relationship("RepoStats", back_populates="repository")

    def __repr__(self):
        return f"<Repository {self.name}>"


class RepoConfig(Base):
    """Repository config model - 仓库配置表"""

    __tablename__ = "repo_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)

    # Config type: route, auth, rate_limit, transform
    config_type = Column(String(50), nullable=False, index=True)

    # Config data
    config_key = Column(String(100), nullable=False)
    config_value = Column(JSONB, nullable=False)
    config_order = Column(Integer, default=0)

    # Status
    enabled = Column(Boolean, default=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    repository = relationship("Repository", back_populates="configs")

    def __repr__(self):
        return f"<RepoConfig {self.config_type}:{self.config_key}>"


class RepoPricing(Base):
    """Repository pricing model - 仓库定价表"""

    __tablename__ = "repo_pricing"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Pricing mode: per_call, token, flow, subscription
    pricing_type = Column(String(20), nullable=False)

    # Prices
    price_per_call = Column(String(20), nullable=True)  # Per call price
    price_per_token = Column(String(20), nullable=True)  # Per token price
    price_per_mb = Column(String(20), nullable=True)  # Per MB price
    monthly_price = Column(String(20), nullable=True)  # Monthly subscription price
    yearly_price = Column(String(20), nullable=True)  # Yearly subscription price

    # Free quota
    free_calls = Column(Integer, default=0)  # Free calls
    free_tokens = Column(Integer, default=0)  # Free tokens
    free_quota_days = Column(Integer, default=0)  # Free trial days

    # Packages (JSON array)
    packages = Column(JSONB, default=list)

    # Status
    status = Column(String(20), default="active")

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    repository = relationship("Repository", back_populates="pricing")

    def __repr__(self):
        return f"<RepoPricing {self.pricing_type}>"


class RepoStats(Base):
    """Repository stats model - 仓库统计表（按小时聚合）"""

    __tablename__ = "repo_stats"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)

    # Time dimension
    stat_hour = Column(DateTime, nullable=False)

    # Call statistics
    total_calls = Column(BigInteger, default=0)
    success_calls = Column(BigInteger, default=0)
    failed_calls = Column(BigInteger, default=0)

    # Performance statistics
    avg_latency_ms = Column(String(20), nullable=True)
    p50_latency_ms = Column(Integer, nullable=True)
    p90_latency_ms = Column(Integer, nullable=True)
    p99_latency_ms = Column(Integer, nullable=True)
    max_latency_ms = Column(Integer, nullable=True)

    # Traffic statistics
    total_bytes = Column(BigInteger, default=0)
    total_tokens = Column(BigInteger, default=0)

    # Cost statistics
    total_cost = Column(String(20), default="0")

    # Unique callers
    unique_keys = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)

    # Relationships
    repository = relationship("Repository", back_populates="stats")

    def __repr__(self):
        return f"<RepoStats {self.repo_id}:{self.stat_hour}>"
