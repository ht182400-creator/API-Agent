"""Payment Service - 支付服务"""

import uuid
import json
import hashlib
import time
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from src.models.payment import Payment, RechargePackage
from src.models.billing import Account, Bill
from src.core.exceptions import (
    ValidationError,
    NotFoundError,
    PaymentError,
    InvalidParameterError,
)
from src.config.logging_config import get_logger


class PaymentService:
    """支付服务 - 核心业务逻辑"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
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
    
    # ==================== 充值套餐管理 ====================
    
    async def list_packages(self, is_active: bool = True) -> List[RechargePackage]:
        """
        获取可用充值套餐列表
        
        Args:
            is_active: 是否只显示启用状态
            
        Returns:
            套餐列表
        """
        query = select(RechargePackage)
        
        if is_active:
            query = query.where(RechargePackage.is_active == "true")
        
        query = query.order_by(RechargePackage.sort_order.asc())
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_package(self, package_id: str) -> Optional[RechargePackage]:
        """
        获取套餐详情
        
        Args:
            package_id: 套餐ID
            
        Returns:
            套餐信息
        """
        result = await self.db.execute(
            select(RechargePackage).where(RechargePackage.id == package_id)
        )
        return result.scalar_one_or_none()
    
    async def create_package(
        self,
        name: str,
        price: float,
        original_amount: float = None,
        bonus_amount: str = "0",
        bonus_ratio: str = None,
        validity_days: int = None,
        description: str = None,
        is_featured: bool = False,
    ) -> RechargePackage:
        """
        创建充值套餐
        
        Args:
            name: 套餐名称
            price: 售价
            original_amount: 原价
            bonus_amount: 赠送金额
            bonus_ratio: 赠送比例
            validity_days: 有效期天数
            description: 描述
            is_featured: 是否推荐
            
        Returns:
            创建的套餐
        """
        package = RechargePackage(
            name=name,
            original_amount=str(original_amount or price),
            price=str(price),
            bonus_amount=bonus_amount,
            bonus_ratio=bonus_ratio,
            validity_days=validity_days,
            description=description,
            is_featured="true" if is_featured else "false",
        )
        
        self.db.add(package)
        await self.db.commit()
        await self.db.refresh(package)
        
        return package
    
    # ==================== 充值配置验证 ====================
    
    async def validate_recharge_amount(self, amount: float, package_id: str = None) -> Tuple[bool, str]:
        """
        验证充值金额是否合法
        
        Args:
            amount: 充值金额
            package_id: 套餐ID（可选）
            
        Returns:
            (是否合法, 错误消息)
        """
        from src.config.settings import settings
        
        # 全局最小/最大金额限制
        if amount < settings.recharge_min_amount:
            return False, f"充值金额不能低于 {settings.recharge_min_amount} 元"
        
        if amount > settings.recharge_max_amount:
            return False, f"充值金额不能超过 {settings.recharge_max_amount} 元"
        
        # 如果指定了套餐，检查套餐的金额限制
        if package_id:
            package = await self.get_package(package_id)
            if package:
                if package.min_amount and amount < float(package.min_amount):
                    return False, f"该套餐最低充值 {package.min_amount} 元"
                if package.max_amount and amount > float(package.max_amount):
                    return False, f"该套餐最高充值 {package.max_amount} 元"
        
        return True, ""
    
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
        # 这里是模拟实现，实际应该调用支付宝/微信等支付接口
        base_url = "https://pay.example.com"
        
        if payment_method == "alipay":
            return f"{base_url}/alipay?order_no={payment.order_no}&amount={payment.amount}"
        elif payment_method == "wechat":
            return f"{base_url}/wechat?order_no={payment.order_no}&amount={payment.amount}"
        elif payment_method == "paypal":
            return f"{base_url}/paypal?order_no={payment.order_no}&amount={payment.amount}"
        else:
            return f"{base_url}/checkout?order_no={payment.order_no}"
    
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
    
    # ==================== 支付回调处理 ====================
    
    async def handle_payment_callback(
        self,
        payment_no: str,
        transaction_id: str,
        status: str,
        payer_info: dict = None,
        raw_data: dict = None,
    ) -> bool:
        """
        处理支付回调
        
        Args:
            payment_no: 支付单号
            transaction_id: 第三方交易号
            status: 支付状态 (success/failed)
            payer_info: 支付人信息
            raw_data: 原始回调数据
            
        Returns:
            是否处理成功
        """
        payment = await self.query_payment(payment_no)
        if not payment:
            raise NotFoundError("支付记录不存在")
        
        if payment.status != "pending":
            # 已处理过的回调，忽略
            return True
        
        # 更新支付状态
        if status == "success":
            payment.status = "completed"
            payment.transaction_id = transaction_id
            payment.pay_time = datetime.utcnow()
            payment.payer_info = json.dumps(payer_info) if payer_info else None
            
            # 扣除余额并发放套餐
            await self._process_successful_payment(payment)
        else:
            payment.status = "failed"
        
        payment.callback_status = "processed"
        payment.callback_response = json.dumps(raw_data) if raw_data else None
        
        await self.db.commit()
        return True
    
    async def _process_successful_payment(self, payment: Payment) -> None:
        """
        处理成功支付的逻辑：增加账户余额
        
        Args:
            payment: 支付记录
        """
        from src.services.account_service import AccountService
        from src.config.settings import settings
        
        # 支付方式映射
        payment_method_map = {
            "alipay": "支付宝",
            "wechat": "微信支付",
            "bankcard": "银行卡",
            "paypal": "PayPal",
        }
        payment_method_name = payment_method_map.get(payment.payment_method, payment.payment_method or "未知")
        
        # 计算到账金额（本金 + 赠送）
        principal = float(payment.amount)  # 本金
        
        # 获取充值套餐信息（如果有）
        package = None
        package_name = "自定义充值"
        bonus = 0.0
        
        if payment.package_id:
            package = await self.get_package(str(payment.package_id))
        
        if package:
            package_name = package.name
            bonus = float(package.bonus_amount) if package.bonus_amount else 0
            
            # 如果有赠送比例
            if package.bonus_ratio and float(package.bonus_ratio) > 0:
                bonus = principal * float(package.bonus_ratio)
        else:
            # 自定义充值，使用全局赠送比例
            if settings.recharge_default_bonus_ratio > 0:
                bonus = principal * settings.recharge_default_bonus_ratio
        
        total_amount = principal + bonus
        
        # 生成描述（包含支付方式）
        if bonus > 0:
            description = f"{payment_method_name}充值：{package_name}，本金{principal:.2f}元，赠送{bonus:.2f}元"
        else:
            description = f"{payment_method_name}充值：{package_name}，金额{principal:.2f}元"
        
        # 更新账户余额（account_service.add_balance 内部已创建 Bill）
        account_service = AccountService(self.db)
        await account_service.add_balance(
            user_id=str(payment.user_id),
            amount=total_amount,
            source_type="recharge",
            source_id=str(payment.id),
            description=description,
        )
        
        # 【V4.0 新增】充值成功后，自动升级普通用户为开发者
        await self._upgrade_user_after_recharge(str(payment.user_id))
    
    async def _upgrade_user_after_recharge(self, user_id: str) -> None:
        """
        充值成功后升级用户为开发者
        
        Args:
            user_id: 用户ID
        """
        from src.models.user import User
        from sqlalchemy import select
        
        logger = get_logger("payment")
        logger.info(f"[Recharge-Upgrade] Starting: user_id={user_id}")
        
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            logger.warning(f"[Recharge-Upgrade] User not found: user_id={user_id}")
            return
        
        logger.info(f"[Recharge-Upgrade] User found: email={user.email}, role={user.role}, user_type={user.user_type}")
        
        if user.role == "user":
            # 【场景1】普通用户充值后自动升级为开发者
            old_role = user.role
            old_user_type = user.user_type
            user.role = "developer"
            user.user_type = "developer"
            user.updated_at = datetime.utcnow()
            # 【重要】立即 flush 确保修改被写入数据库（后续 commit 会统一提交）
            await self.db.flush()
            logger.info(f"[Recharge-Upgrade] UPGRADED: {user.email} role {old_role}->developer, user_type {old_user_type}->developer")
        else:
            # 【场景2】开发者续费，无需升级操作
            logger.info(f"[Recharge-Upgrade] SKIP: User {user.email} has role={user.role}, not 'user'")
    
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
    
    # ==================== 初始化默认套餐 ====================
    
    async def init_default_packages(self) -> List[RechargePackage]:
        """
        初始化默认充值套餐
        
        Returns:
            创建的套餐列表
        """
        packages = [
            {
                "name": "基础套餐",
                "price": 10.0,
                "bonus_amount": "0",
                "description": "10元 = 100次调用额度",
                "included_calls": 100,
                "is_featured": False,
            },
            {
                "name": "标准套餐",
                "price": 50.0,
                "bonus_amount": "5",
                "description": "50元 = 550次调用额度（送10%）",
                "included_calls": 500,
                "bonus_ratio": "0.1",
                "is_featured": True,
            },
            {
                "name": "高级套餐",
                "price": 100.0,
                "bonus_amount": "15",
                "description": "100元 = 1200次调用额度（送15%）",
                "included_calls": 1000,
                "bonus_ratio": "0.15",
                "is_featured": False,
            },
            {
                "name": "企业套餐",
                "price": 500.0,
                "bonus_amount": "100",
                "description": "500元 = 7000次调用额度（送20%）",
                "included_calls": 5000,
                "bonus_ratio": "0.2",
                "validity_days": 365,
                "is_featured": False,
            },
        ]
        
        created_packages = []
        for i, pkg_data in enumerate(packages):
            pkg = await self.create_package(
                **pkg_data,
                sort_order=i,
            )
            created_packages.append(pkg)
        
        return created_packages
    
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
        payment_url = f"https://pay.example.com/custom?order_no={order_no}&amount={amount}"
        
        return payment, payment_url
