"""Pricing config model - 计费配置表"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, Numeric, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.config.database import Base


class PricingConfig(Base):
    """计费配置表 - 支持灵活的计费模式配置

    支持三种计费模式：
    1. call - 按调用次数计费
    2. token - 按Token数计费
    3. package - 套餐包计费

    优先级规则：数字越小优先级越高
    """

    __tablename__ = "pricing_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 仓库关联
    repo_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="关联的仓库ID，NULL表示全局默认配置"
    )

    # 计费模式：call(按调用), token(按Token), package(套餐包)
    pricing_type = Column(String(20), nullable=False, index=True)

    # ===== 按调用计费模式 (pricing_type='call') =====
    price_per_call = Column(
        Numeric(10, 4),
        nullable=True,
        comment="每次调用价格"
    )
    free_calls = Column(
        Integer,
        default=0,
        comment="免费调用次数"
    )

    # ===== 按Token计费模式 (pricing_type='token') =====
    price_per_1k_input_tokens = Column(
        Numeric(10, 4),
        nullable=True,
        comment="每1K输入Token价格"
    )
    price_per_1k_output_tokens = Column(
        Numeric(10, 4),
        nullable=True,
        comment="每1K输出Token价格"
    )
    free_input_tokens = Column(
        Integer,
        default=0,
        comment="免费输入Token数"
    )
    free_output_tokens = Column(
        Integer,
        default=0,
        comment="免费输出Token数"
    )

    # ===== 套餐包计费模式 (pricing_type='package') =====
    # 套餐包定义 (JSON格式)
    # [
    #   {"name": "基础套餐", "calls": 1000, "price": 10.00, "period_days": 30},
    #   {"name": "高级套餐", "calls": 10000, "price": 80.00, "period_days": 30},
    # ]
    packages = Column(
        JSONB,
        default=list,
        comment="套餐包定义"
    )
    default_package_id = Column(
        String(50),
        nullable=True,
        comment="默认选中的套餐包ID"
    )

    # ===== 通用配置 =====
    # 计费阶梯 (JSON格式，支持阶梯定价)
    # [
    #   {"min_calls": 0, "max_calls": 10000, "discount": 1.0},
    #   {"min_calls": 10001, "max_calls": 100000, "discount": 0.9},
    #   {"min_calls": 100001, "max_calls": null, "discount": 0.8}
    # ]
    pricing_tiers = Column(
        JSONB,
        default=list,
        comment="阶梯定价配置"
    )

    # VIP等级折扣 (JSON格式)
    # {"1": 1.0, "2": 0.95, "3": 0.9}
    vip_discounts = Column(
        JSONB,
        default=dict,
        comment="VIP等级折扣配置"
    )

    # 优先级：数字越小优先级越高
    priority = Column(
        Integer,
        default=100,
        comment="配置优先级，数字越小优先级越高"
    )

    # 生效时间范围
    valid_from = Column(
        DateTime,
        nullable=True,
        comment="配置生效开始时间"
    )
    valid_until = Column(
        DateTime,
        nullable=True,
        comment="配置生效结束时间"
    )

    # 状态：active(生效), inactive(失效), deprecated(废弃)
    status = Column(
        String(20),
        default="active",
        index=True
    )

    # 备注
    description = Column(
        Text,
        nullable=True,
        comment="配置说明"
    )

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), nullable=True, comment="创建人")

    # Relationships
    repository = relationship("Repository", back_populates="pricing_configs")

    def __repr__(self):
        return f"<PricingConfig {self.pricing_type}:{self.repo_id}>"

    def is_valid(self) -> bool:
        """检查配置是否在有效期内"""
        now = datetime.utcnow()
        if self.status != "active":
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def get_vip_discount(self, vip_level: int) -> float:
        """获取指定VIP等级对应的折扣"""
        discounts = self.vip_discounts or {}
        return float(discounts.get(str(vip_level), 1.0))

    def get_tier_discount(self, usage_count: int) -> float:
        """获取指定用量对应的阶梯折扣"""
        tiers = self.pricing_tiers or []
        for tier in sorted(tiers, key=lambda x: x.get("min_calls", 0)):
            min_calls = tier.get("min_calls", 0)
            max_calls = tier.get("max_calls")
            if usage_count >= min_calls and (max_calls is None or usage_count <= max_calls):
                return float(tier.get("discount", 1.0))
        return 1.0

    def calculate_cost(
        self,
        call_count: int = 1,
        input_tokens: int = 0,
        output_tokens: int = 0,
        vip_level: int = 0
    ) -> float:
        """计算费用

        Args:
            call_count: 调用次数
            input_tokens: 输入Token数
            output_tokens: 输出Token数
            vip_level: VIP等级

        Returns:
            计算后的费用
        """
        if not self.is_valid():
            return 0.0

        total_cost = 0.0

        if self.pricing_type == "call":
            # 按调用计费
            billable_calls = max(0, call_count - self.free_calls)
            unit_price = float(self.price_per_call or 0)
            total_cost = billable_calls * unit_price

        elif self.pricing_type == "token":
            # 按Token计费
            billable_input = max(0, input_tokens - self.free_input_tokens)
            billable_output = max(0, output_tokens - self.free_output_tokens)
            input_price = float(self.price_per_1k_input_tokens or 0) / 1000
            output_price = float(self.price_per_1k_output_tokens or 0) / 1000
            total_cost = billable_input * input_price + billable_output * output_price

        elif self.pricing_type == "package":
            # 套餐包计费在扣费时单独处理
            total_cost = 0.0

        # 应用阶梯折扣
        tier_discount = self.get_tier_discount(call_count)
        total_cost *= tier_discount

        # 应用VIP折扣
        vip_discount = self.get_vip_discount(vip_level)
        total_cost *= vip_discount

        return round(total_cost, 4)
