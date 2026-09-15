"""
支付查询：按支付单号/订单号查询、用户支付列表（分页）

由 `scripts/dev/split_payment_service.py` 从 `payment_service.py` 精确搬移生成，
方法体与原实现逐字一致（仅移动位置）。

⚠️ 依赖宿主类提供 ``self.db``（由 :class:`PaymentService` 组合）。
"""

import uuid
from typing import Optional, List, Tuple
from sqlalchemy import select, func
from src.models.payment import Payment
from src.config.logging_config import get_logger

logger = get_logger("payment")


class PaymentQueryMixin:
    """支付查询：按支付单号/订单号查询、用户支付列表（分页）"""

    
    async def query_payment(self, payment_no: str) -> Optional[Payment]:
        """
        查询支付状态
        
        Args:
            payment_no: 支付单号
            
        Returns:
            支付记录
        """
        result = await self.db.execute(
            select(Payment).where(Payment.payment_no == payment_no)
        )
        return result.scalar_one_or_none()
    
    async def query_payment_by_order(self, order_no: str) -> Optional[Payment]:
        """
        根据订单号查询支付状态
        
        Args:
            order_no: 订单号
            
        Returns:
            支付记录
        """
        result = await self.db.execute(
            select(Payment).where(Payment.order_no == order_no)
        )
        return result.scalar_one_or_none()
    
    # ==================== 支付记录查询 ====================
    
    async def list_user_payments(
        self,
        user_id: str,
        status: str = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Payment], int]:
        """
        获取用户的支付记录
        
        Args:
            user_id: 用户ID
            status: 支付状态筛选
            page: 页码
            page_size: 每页数量
            
        Returns:
            (支付记录列表, 总数)
        """
        query = select(Payment).where(Payment.user_id == uuid.UUID(user_id))
        
        if status:
            query = query.where(Payment.status == status)
        
        # 统计总数
        count_query = select(func.count(Payment.id)).where(Payment.user_id == uuid.UUID(user_id))
        if status:
            count_query = count_query.where(Payment.status == status)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 分页查询
        query = query.order_by(Payment.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        payments = result.scalars().all()
        
        return payments, total
