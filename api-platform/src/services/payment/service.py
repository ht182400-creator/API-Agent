"""
支付服务 - 组合入口

P1-4 拆分：原 1170 行的单文件按子域拆为同包内的多个 Mixin；
本类只负责组合与 ``self.db`` 注入，各子域实现见同包 ``_*.py``。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.payment._orders import PaymentOrdersMixin
from src.services.payment._packages import PaymentPackagesMixin
from src.services.payment._alipay import PaymentAlipayMixin
from src.services.payment._callback import PaymentCallbackMixin
from src.services.payment._query import PaymentQueryMixin


class PaymentService(
    PaymentOrdersMixin,
    PaymentPackagesMixin,
    PaymentAlipayMixin,
    PaymentCallbackMixin,
    PaymentQueryMixin,
):
    """支付服务 - 核心业务逻辑（各子域实现见同包 _*.py）"""

    def __init__(self, db: AsyncSession):
        self.db = db
