"""Billing model - 计费模型"""

import uuid
from src.utils.helpers import get_utc_now
from typing import Optional

from sqlalchemy import Column, String, DateTime, Text, BigInteger, ForeignKey, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.config.database import Base
from src.config.logging_config import get_logger

logger = get_logger("billing")


def _current_billing_environment() -> str:
    """
    账单环境标识的运行时取值（作为 SQLAlchemy column default 使用）。

    背景（防漏传设计）：
        旧实现把 environment 的默认值**硬编码**为 "simulation"。
        一旦某个写入点漏传 environment，生产环境的账单会被静默写成 simulation，
        而默认查询只看 production → 这笔账"消失"（对账漏账），且**无任何报错**。

        现改为默认值**跟随运行环境**（settings.billing_environment）：
            - 生产环境漏传 → "production"（不会漏账）
            - 开发/预发漏传 → "simulation"（语义正确）

        即：默认值指向"当前上下文"，而不是某个固定值 ——
        固定值必然在某个环境下变成错误答案。

    注意：函数内延迟 import，避免 models → config.settings 的循环导入。
    """
    try:
        from src.config.settings import settings

        return settings.billing_environment
    except Exception:  # pragma: no cover - 配置未就绪时降级
        return "simulation"


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
    created_at = Column(DateTime(timezone=True), default=get_utc_now())
    updated_at = Column(DateTime(timezone=True), default=get_utc_now(), onupdate=get_utc_now())

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

    # Environment flag: simulation, production (区分模拟/真实环境)
    # 注意：默认值**跟随运行环境**（见 _current_billing_environment），
    #       避免漏传时被静默写成错误环境导致对账漏账。
    environment = Column(String(20), default=_current_billing_environment, index=True)

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
    created_at = Column(DateTime(timezone=True), default=get_utc_now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

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
    reset_at = Column(DateTime(timezone=True), nullable=True)

    # Audit fields
    created_at = Column(DateTime(timezone=True), default=get_utc_now())
    updated_at = Column(DateTime(timezone=True), default=get_utc_now(), onupdate=get_utc_now())

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

    # 请求追踪ID (由 middleware 生成的全链路追踪ID)
    request_id = Column(String(64), nullable=True, index=True)

    # Foreign keys
    repo_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Request information
    endpoint = Column(String(255), nullable=True)
    method = Column(String(10), nullable=True)
    request_path = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)
    request_params = Column(Text, nullable=True)  # JSON字符串格式的请求参数

    # Tester information - 测试人员
    tester = Column(String(100), nullable=True)  # 测试人员用户名

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
    created_at = Column(DateTime(timezone=True), default=get_utc_now(), index=True)

    def __repr__(self):
        return f"<APICallLog {self.id}:{self.endpoint}>"


class MonthlyBill(Base):
    """Monthly Bill model - 月度账单汇总表"""

    __tablename__ = "monthly_bills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 关联信息
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 账单周期
    year = Column(BigInteger, nullable=False)
    month = Column(BigInteger, nullable=False)

    # 环境标识
    # 注意：默认值**跟随运行环境**（见 _current_billing_environment）
    environment = Column(String(20), default=_current_billing_environment, index=True)

    # 账单统计
    total_recharge = Column(String(20), default="0")  # 本月充值总额
    total_consumption = Column(String(20), default="0")  # 本月消费总额
    net_change = Column(String(20), default="0")  # 净变化（充值-消费）
    beginning_balance = Column(String(20), default="0")  # 期初余额
    ending_balance = Column(String(20), default="0")  # 期末余额

    # 使用统计
    total_calls = Column(BigInteger, default=0)  # 总调用次数
    total_tokens = Column(BigInteger, default=0)  # 总Token数

    # 账单详情（JSON格式存储按仓库/按类型分类的明细）
    details = Column(Text, nullable=True)  # JSON: {"by_repository": [...], "by_type": [...]}

    # 账单状态: pending(待生成), generated(已生成), reviewed(已审核), published(已发布)
    status = Column(String(20), default="pending", index=True)

    # 审核信息
    reviewed_by = Column(UUID(as_uuid=True), nullable=True)  # 审核人
    reviewed_at = Column(DateTime(timezone=True), nullable=True)  # 审核时间
    review_comment = Column(Text, nullable=True)  # 审核备注

    # 生成信息
    generated_by = Column(UUID(as_uuid=True), nullable=True)  # 生成人
    generated_at = Column(DateTime(timezone=True), nullable=True)  # 生成时间

    # 发布信息
    published_at = Column(DateTime(timezone=True), nullable=True)  # 发布时间

    # 审计字段
    created_at = Column(DateTime(timezone=True), default=get_utc_now())
    updated_at = Column(DateTime(timezone=True), default=get_utc_now(), onupdate=get_utc_now())

    # Relationships
    user = relationship("User", back_populates="monthly_bills")

    def __repr__(self):
        return f"<MonthlyBill {self.user_id}:{self.year}-{self.month:02d}>"


# ==================== 账单写入守卫（防跨环境静默写入） ====================

def _guard_environment_on_insert(target, model_name: str) -> None:
    """
    账单写入守卫（SQLAlchemy ``before_insert`` 钩子）。

    作用（L1「默认值跟随环境」之外的**兜底**）：

        1. 若 ``environment`` 为空 → 按当前环境补全（避免 None 落库）；
        2. **生产环境写入 simulation 账单 → 记录 ERROR 日志**（明显提示）。

    为什么需要：
        账单环境写错是典型的"**静默失败**" —— 数据不报错，只是落进另一个环境，
        默认查询看不到，最终表现为**对账漏账**，且极难发现。
        这类问题必须让它"发声"。

    注意：
        - 事件在 flush 阶段触发，此时 column default 可能尚未应用，
          因此这里同时处理"为空"与"值不符"两种情况；
        - 若确需在生产库补录历史 simulation 数据，出现该 ERROR 属预期，
          可按日志中的 bill_no / user_id 核对来源。
    """
    from src.config.settings import settings

    current = settings.billing_environment

    if not target.environment:
        target.environment = current
        logger.warning(
            "[账单环境] %s 未显式指定 environment，已按当前环境补全为 '%s'",
            model_name,
            current,
        )
        return

    if settings.is_production and target.environment == "simulation":
        logger.error(
            "[账单环境异常] 生产环境正在写入 simulation 账单！"
            "model=%s bill_no=%s amount=%s user_id=%s —— "
            "请检查是否存在漏传 environment 的写入点",
            model_name,
            getattr(target, "bill_no", None) or getattr(target, "id", None),
            getattr(target, "amount", None),
            getattr(target, "user_id", None),
        )


@event.listens_for(Bill, "before_insert")
def _bill_before_insert(mapper, connection, target):
    """Bill 写入守卫"""
    _guard_environment_on_insert(target, "Bill")


@event.listens_for(MonthlyBill, "before_insert")
def _monthly_bill_before_insert(mapper, connection, target):
    """MonthlyBill 写入守卫"""
    _guard_environment_on_insert(target, "MonthlyBill")
