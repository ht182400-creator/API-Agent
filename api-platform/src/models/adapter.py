"""Adapter model - 适配器模型"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.config.database import Base


class Adapter(Base):
    """Adapter model - 适配器表"""

    __tablename__ = "adapters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Adapter information
    name = Column(String(100), nullable=False)
    adapter_type = Column(String(50), nullable=False, index=True)  # http, grpc, websocket, graphql, soap

    # Version
    version = Column(String(20), nullable=False)

    # Configuration
    config_schema = Column(JSONB, nullable=False)  # Configuration JSON Schema
    default_config = Column(JSONB, default=dict)

    # Capabilities
    capabilities = Column(JSONB, default=dict)
    # Example: {"auth": ["api_key", "oauth"], "transform": true, "websocket": false}

    # Status: active, deprecated
    status = Column(String(20), default="active", index=True)

    # Statistics
    total_repos = Column(Integer, default=0)  # Number of repositories using this adapter

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Adapter {self.name}:{self.version}>"


class AdapterInstance(Base):
    """Adapter instance model - 适配器实例表"""

    __tablename__ = "adapter_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    adapter_id = Column(UUID(as_uuid=True), nullable=False)

    # Instance configuration
    instance_config = Column(JSONB, default=dict)

    # Status
    status = Column(String(20), default="active")  # active, disabled, error

    # Health check
    health_status = Column(String(20), default="unknown")  # healthy, unhealthy, unknown
    last_health_check = Column(DateTime, nullable=True)
    health_check_interval = Column(Integer, default=60)  # seconds

    # Statistics
    total_calls = Column(Integer, default=0)
    failed_calls = Column(Integer, default=0)
    avg_latency_ms = Column(Integer, nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AdapterInstance {self.repo_id}:{self.adapter_id}>"
