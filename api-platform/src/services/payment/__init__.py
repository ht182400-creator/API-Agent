"""
支付服务包

P1-4 拆分产物：对外接口为 ``from src.services.payment import PaymentService``。
"""

from src.services.payment.service import PaymentService

__all__ = ["PaymentService"]
