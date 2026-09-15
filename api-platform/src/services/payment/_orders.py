"""
支付/订单生命周期：单号生成、下单、支付链接、取消、退款、自定义充值

由 `scripts/dev/split_payment_service.py` 从 `payment_service.py` 精确搬移生成，
方法体与原实现逐字一致（仅移动位置）。

⚠️ 依赖宿主类提供 ``self.db``（由 :class:`PaymentService` 组合）。
"""

import uuid
import time
from typing import Tuple
from src.models.payment import Payment, RechargePackage
from src.core.exceptions import ValidationError, NotFoundError
from src.config.logging_config import get_logger

logger = get_logger("payment")


class PaymentOrdersMixin:
    """支付/订单生命周期：单号生成、下单、支付链接、取消、退款、自定义充值"""

    
    def generate_payment_no(self) -> str:
        """生成支付单号"""
        timestamp = int(time.time())
        random_str = uuid.uuid4().hex[:8].upper()
        return f"PAY{timestamp}{random_str}"
    
    def generate_order_no(self) -> str:
        """生成订单号"""
        timestamp = int(time.time())
        random_str = uuid.uuid4().hex[:6].upper()
        return f"ORD{timestamp}{random_str}"
    
    # ==================== 支付流程 ====================
    
    async def create_payment(
        self,
        user_id: str,
        package_id: str,
        payment_method: str = "alipay",
        callback_url: str = None,
        description: str = None,
    ) -> Tuple[Payment, str]:
        """
        创建支付订单
        
        Args:
            user_id: 用户ID
            package_id: 套餐ID
            payment_method: 支付方式 (alipay/wechat/paypal)
            callback_url: 回调通知地址
            description: 订单描述
            
        Returns:
            (Payment对象, 支付跳转URL或二维码链接)
        """
        # 获取套餐信息
        package = await self.get_package(package_id)
        if not package:
            raise NotFoundError("套餐不存在")
        
        if package.is_active != "true":
            raise ValidationError("套餐已下架")
        
        # 生成订单号
        order_no = self.generate_order_no()
        payment_no = self.generate_payment_no()
        
        # 创建支付记录
        payment = Payment(
            payment_no=payment_no,
            order_no=order_no,
            user_id=uuid.UUID(user_id),
            payment_type="recharge",
            amount=package.price,
            currency="CNY",
            package_id=package.id,
            package_name=package.name,
            payment_method=payment_method,
            payment_channel="official",
            status="pending",
            callback_url=callback_url,
            description=description or f"充值{package.name}",
        )
        
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        
        # 生成支付链接（模拟实现）
        payment_url = await self._generate_payment_url(payment, package, payment_method)
        
        return payment, payment_url
    
    async def _generate_payment_url(
        self,
        payment: Payment,
        package: RechargePackage,
        payment_method: str,
    ) -> str:
        """
        生成支付链接（实际项目中应该调用第三方支付SDK）
        
        Args:
            payment: 支付记录
            package: 充值套餐
            payment_method: 支付方式
            
        Returns:
            支付跳转链接或二维码内容
        """
        from src.config.settings import settings
        
        # 支付宝支付
        if payment_method == "alipay":
            return await self._generate_alipay_url(payment, package)
        
        # 微信支付（暂未实现）
        if payment_method == "wechat":
            return f"https://pay.example.com/wechat?order_no={payment.order_no}&amount={payment.amount}"
        
        # PayPal（暂未实现）
        if payment_method == "paypal":
            return f"https://pay.example.com/paypal?order_no={payment.order_no}&amount={payment.amount}"
        
        # 默认
        return f"https://pay.example.com/checkout?order_no={payment.order_no}"
    
    # ==================== 支付取消/退款 ====================
    
    async def cancel_payment(self, payment_no: str, user_id: str) -> Payment:
        """
        取消支付订单
        
        Args:
            payment_no: 支付单号
            user_id: 用户ID（用于权限验证）
            
        Returns:
            更新后的支付记录
        """
        payment = await self.query_payment(payment_no)
        
        if not payment:
            raise NotFoundError("支付记录不存在")
        
        if str(payment.user_id) != user_id:
            raise ValidationError("无权操作此订单")
        
        if payment.status != "pending":
            raise ValidationError(f"订单状态为{payment.status}，无法取消")
        
        payment.status = "cancelled"
        await self.db.commit()
        await self.db.refresh(payment)
        
        return payment
    
    async def refund_payment(
        self,
        payment_no: str,
        reason: str,
        operator_id: str = None,
    ) -> Payment:
        """
        退款（需要管理员权限）
        
        Args:
            payment_no: 支付单号
            reason: 退款原因
            operator_id: 操作员ID
            
        Returns:
            更新后的支付记录
        """
        payment = await self.query_payment(payment_no)
        
        if not payment:
            raise NotFoundError("支付记录不存在")
        
        if payment.status != "completed":
            raise ValidationError(f"订单状态为{payment.status}，无法退款")
        
        if payment.status == "refunded":
            raise ValidationError("订单已退款")
        
        # 扣除账户余额（需要实现）
        from src.services.account_service import AccountService
        
        account_service = AccountService(self.db)
        await account_service.deduct_balance(
            user_id=str(payment.user_id),
            amount=float(payment.amount),
            source_type="refund",
            source_id=str(payment.id),
            description=f"退款：{reason}",
        )
        
        # 更新支付状态
        payment.status = "refunded"
        payment.remark = f"退款原因：{reason}"
        await self.db.commit()
        await self.db.refresh(payment)
        
        return payment
    
    # ==================== 自定义金额充值 ====================
    
    async def create_custom_recharge(
        self,
        user_id: str,
        amount: float,
        payment_method: str = "alipay",
    ) -> Tuple[Payment, str]:
        """
        创建自定义金额充值订单
        
        Args:
            user_id: 用户ID
            amount: 充值金额
            payment_method: 支付方式
            
        Returns:
            (Payment对象, 支付跳转URL)
        """
        from src.config.settings import settings
        
        # 验证金额
        valid, msg = await self.validate_recharge_amount(amount)
        if not valid:
            raise ValidationError(msg)
        
        # 计算赠送金额
        bonus = 0.0
        if settings.recharge_default_bonus_ratio > 0:
            bonus = amount * settings.recharge_default_bonus_ratio
        
        # 生成订单号
        order_no = self.generate_order_no()
        payment_no = self.generate_payment_no()
        
        # 计算到账金额
        total_amount = amount + bonus
        
        # 创建支付记录
        payment = Payment(
            payment_no=payment_no,
            order_no=order_no,
            user_id=uuid.UUID(user_id),
            payment_type="recharge",
            amount=str(amount),
            currency="CNY",
            payment_method=payment_method,
            payment_channel="official",
            status="pending",
            description=f"自定义充值：{amount}元" + (f"，赠送{bonus}元" if bonus > 0 else ""),
        )
        
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        
        # 生成支付链接
        if payment_method == "alipay":
            # 调用支付宝生成真实支付链接
            payment_url = await self._generate_alipay_url(payment, None)
        else:
            payment_url = f"https://pay.example.com/custom?order_no={order_no}&amount={amount}"
        
        return payment, payment_url
