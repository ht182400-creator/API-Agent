"""Payment Service - 支付服务"""

import asyncio
import uuid
import json
import hashlib
import time
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
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

# 支付模块日志记录器
logger = get_logger("payment")


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
    
    async def _generate_alipay_url(self, payment: Payment, package: RechargePackage) -> str:
        """
        生成支付宝支付链接
        
        Args:
            payment: 支付记录
            package: 充值套餐
            
        Returns:
            支付宝PC端支付链接
        """
        from src.config.settings import settings
        
        # 检查是否配置了支付宝
        if not settings.alipay_app_id or not settings.get_alipay_private_key() or not settings.get_alipay_public_key():
            logger.warning(
                "支付宝未配置，使用模拟支付链接 | order_no=%s, amount=%s",
                payment.order_no,
                payment.amount
            )
            # 未配置，返回模拟链接
            return f"https://pay.example.com/alipay?order_no={payment.order_no}&amount={payment.amount}"
        
        try:
            from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
            from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
            from alipay.aop.api.request.AlipayTradePagePayRequest import AlipayTradePagePayRequest
            from alipay.aop.api.domain.AlipayTradePagePayModel import AlipayTradePagePayModel
            
            # 根据环境选择网关地址（从配置读取）
            gateway = settings.alipay_sandbox_gateway if settings.alipay_sandbox else settings.alipay_production_gateway
            
            # 配置支付宝客户端
            alipay_client_config = AlipayClientConfig()
            alipay_client_config.app_id = settings.alipay_app_id
            alipay_client_config.app_private_key = settings.get_alipay_private_key()
            alipay_client_config.alipay_public_key = settings.get_alipay_public_key()
            alipay_client_config.server_url = gateway
            alipay_client_config.sign_type = "RSA2"
            
            # 初始化支付宝客户端
            client = DefaultAlipayClient(alipay_client_config)
            
            # 构建支付请求
            subject = package.name if package else "账户充值"
            
            # 创建支付模型
            model = AlipayTradePagePayModel()
            model.out_trade_no = payment.order_no
            model.total_amount = str(payment.amount)
            model.subject = subject
            model.product_code = "FAST_INSTANT_TRADE_PAY"
            
            # 创建PC端支付请求
            request = AlipayTradePagePayRequest(biz_model=model)
            request.return_url = settings.alipay_return_url
            request.notify_url = settings.alipay_notify_url
            
            # 获取支付链接
            pay_url = client.page_execute(request, http_method="GET")
            
            logger.info("支付宝支付链接生成成功 | order_no=%s", payment.order_no)
            
            return pay_url
            
        except Exception as e:
            logger.error(
                "支付宝支付链接生成失败 | order_no=%s, error=%s",
                payment.order_no,
                str(e),
                exc_info=True
            )
            raise PaymentError(f"支付链接生成失败: {str(e)}")
    
    async def _generate_alipay_qrcode(self, payment: Payment, package: RechargePackage) -> str:
        """
        生成支付宝扫码支付二维码
        
        Args:
            payment: 支付记录
            package: 充值套餐
            
        Returns:
            二维码图片URL（已转换为base64）
        """
        from src.config.settings import settings
        
        # 检查是否配置了支付宝
        if not settings.alipay_app_id or not settings.get_alipay_private_key() or not settings.get_alipay_public_key():
            logger.warning(
                "支付宝未配置，无法生成二维码 | order_no=%s, amount=%s",
                payment.order_no,
                payment.amount
            )
            raise PaymentError("支付宝未配置")
        
        try:
            from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
            from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
            from alipay.aop.api.request.AlipayTradePrecreateRequest import AlipayTradePrecreateRequest
            from alipay.aop.api.domain.AlipayTradePrecreateModel import AlipayTradePrecreateModel
            import qrcode
            import io
            import base64
            
            # 根据环境选择网关地址
            gateway = settings.alipay_sandbox_gateway if settings.alipay_sandbox else settings.alipay_production_gateway
            
            # 配置支付宝客户端
            alipay_client_config = AlipayClientConfig()
            alipay_client_config.app_id = settings.alipay_app_id
            alipay_client_config.app_private_key = settings.get_alipay_private_key()
            alipay_client_config.alipay_public_key = settings.get_alipay_public_key()
            alipay_client_config.server_url = gateway
            alipay_client_config.sign_type = "RSA2"
            
            # 初始化支付宝客户端
            client = DefaultAlipayClient(alipay_client_config)
            
            # 构建支付请求
            subject = package.name if package else "账户充值"
            
            # 创建扫码支付模型
            model = AlipayTradePrecreateModel()
            model.out_trade_no = payment.order_no
            model.total_amount = str(payment.amount)
            model.subject = subject
            model.store_id = "default_store"
            
            # 创建扫码支付请求
            request = AlipayTradePrecreateRequest(biz_model=model)
            request.notify_url = settings.alipay_notify_url
            
            # 获取二维码URL
            response_str = client.execute(request)
            
            # 解析响应
            import json
            response_data = json.loads(response_str) if isinstance(response_str, str) else response_str
            
            # 支付宝沙箱环境返回的响应没有外层包装
            response = response_data.get('alipay_trade_precreate_response', response_data)
            
            if response.get('code') != '10000':
                logger.error(f"[QRCode] 支付宝返回错误 | code={response.get('code')}, msg={response.get('msg')}")
                raise PaymentError(f"二维码生成失败: {response.get('msg')}")
            
            qr_code = response.get('qr_code')
            logger.info(f"[QRCode] 二维码生成成功 | order_no={payment.order_no}, qr_code={qr_code}")
            
            # 生成二维码图片并转换为base64
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(qr_code)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            # 转换为base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return f"data:image/png;base64,{img_base64}"
            
        except PaymentError:
            raise
        except Exception as e:
            logger.error(
                "支付宝二维码生成失败 | order_no=%s, error=%s",
                payment.order_no,
                str(e),
                exc_info=True
            )
            raise PaymentError(f"二维码生成失败: {str(e)}")
    
    async def generate_alipay_qrcode(self, payment: Payment) -> str:
        """
        生成支付宝扫码二维码（公开方法）
        
        Args:
            payment: 支付记录
            
        Returns:
            二维码图片base64
        """
        # 获取套餐信息
        package = None
        if payment.package_id:
            package = await self.get_package(str(payment.package_id))
        
        return await self._generate_alipay_qrcode(payment, package)
    
    async def refresh_alipay_qrcode(self, payment_no: str) -> str:
        """
        刷新支付宝扫码二维码
        
        当原二维码失效时，重新生成新的二维码。
        
        Args:
            payment_no: 支付单号
            
        Returns:
            新的二维码图片base64
        """
        # 获取支付记录
        payment = await self.query_payment(payment_no)
        if not payment:
            raise NotFoundError("支付记录不存在")
        
        # 检查订单状态，只有pending状态可以刷新二维码
        if payment.status != "pending":
            raise ValidationError(f"订单状态为{payment.status}，无法刷新二维码")
        
        # 检查订单是否过期（10分钟有效期）
        # 数据库存储的是 UTC 时间（aware datetime from get_utc_now()）
        if payment.created_at:
            from datetime import timedelta, timezone
            # 确保 created_at 是 aware datetime
            if payment.created_at.tzinfo is None:
                created_at_utc = payment.created_at.replace(tzinfo=timezone.utc)
            else:
                created_at_utc = payment.created_at
            expiry_time = created_at_utc + timedelta(minutes=10)
            now_utc = datetime.now(timezone.utc)
            if now_utc > expiry_time:
                raise ValidationError("订单已过期，请重新下单")
        
        # 重新生成二维码
        return await self.generate_alipay_qrcode(payment)
    
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
    
    async def query_alipay_trade(self, payment_no: str) -> Optional[Dict[str, Any]]:
        """
        【核心功能】主动查询支付宝交易状态
        
        当本地状态不是成功时，调用支付宝交易查询接口获取真实状态。
        解决异步回调延迟或丢失导致的状态不一致问题。
        
        Args:
            payment_no: 支付单号
            
        Returns:
            支付宝返回的交易状态信息，如果查询失败返回None
        """
        from src.config.settings import settings
        
        # 检查是否配置了支付宝
        if not settings.alipay_app_id or not settings.get_alipay_private_key() or not settings.get_alipay_public_key():
            logger.warning(f"[QueryAlipay] 支付宝未配置，跳过主动查询 | payment_no={payment_no}")
            return None
        
        # 先获取本地订单信息
        payment = await self.query_payment(payment_no)
        if not payment:
            logger.warning(f"[QueryAlipay] 支付记录不存在 | payment_no={payment_no}")
            return None
        
        try:
            from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
            from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
            from alipay.aop.api.request.AlipayTradeQueryRequest import AlipayTradeQueryRequest
            from alipay.aop.api.domain.AlipayTradeQueryModel import AlipayTradeQueryModel
            
            # 根据环境选择网关地址
            gateway = settings.alipay_sandbox_gateway if settings.alipay_sandbox else settings.alipay_production_gateway
            
            # 配置支付宝客户端
            alipay_client_config = AlipayClientConfig()
            alipay_client_config.app_id = settings.alipay_app_id
            alipay_client_config.app_private_key = settings.get_alipay_private_key()
            alipay_client_config.alipay_public_key = settings.get_alipay_public_key()
            alipay_client_config.server_url = gateway
            alipay_client_config.sign_type = "RSA2"
            
            # 初始化支付宝客户端
            client = DefaultAlipayClient(alipay_client_config)
            
            # 创建查询请求
            model = AlipayTradeQueryModel()
            model.out_trade_no = payment.order_no  # 使用商户订单号查询
            
            request = AlipayTradeQueryRequest(biz_model=model)
            
            # 执行查询
            response_str = client.execute(request)
            
            # 支付宝 SDK 返回的是 JSON 字符串，需要解析
            import json
            response_data = json.loads(response_str) if isinstance(response_str, str) else response_str
            
            # 【关键调试】打印原始响应数据
            logger.info(f"[QueryAlipay] 原始响应 | payment_no={payment_no}, response_str={response_str}")
            logger.info(f"[QueryAlipay] 解析后 | payment_no={payment_no}, response_data={response_data}")
            
            # 检查响应状态
            if isinstance(response_data, dict):
                # 支付宝沙箱环境返回的响应没有 alipay_trade_query_response 外层包装
                # 尝试获取 alipay_trade_query_response，如果没有则直接使用根数据
                response = response_data.get('alipay_trade_query_response', response_data)
                trade_status = response.get('trade_status', '')
                
                # 调试：打印完整响应
                logger.info(f"[QueryAlipay] 查询成功 | payment_no={payment_no}, trade_status={trade_status}, response={response}")
                
                # 检查是否有错误码
                if response.get('code') and response.get('code') != '10000':
                    logger.error(f"[QueryAlipay] 支付宝返回错误 | code={response.get('code')}, msg={response.get('msg')}")
                
                return {
                    "trade_status": trade_status,
                    "trade_no": response.get("trade_no", ""),
                    "buyer_logon_id": response.get("buyer_logon_id", ""),
                    "buyer_id": response.get("buyer_id", ""),
                    "total_amount": response.get("total_amount", ""),
                    "gmt_payment": response.get("gmt_payment", ""),
                }
            else:
                logger.error(f"[QueryAlipay] 响应格式异常 | payment_no={payment_no}, response={response_str}")
                return None
            
        except Exception as e:
            logger.error(f"[QueryAlipay] 查询失败 | payment_no={payment_no}, error={str(e)}", exc_info=True)
            return None
    
    async def sync_payment_status_from_alipay(self, payment_no: str) -> Optional[Payment]:
        """
        【核心功能】从支付宝同步支付状态
        
        如果本地状态不是成功，主动查询支付宝并更新本地状态。
        这解决了异步回调不可靠的问题。
        
        Args:
            payment_no: 支付单号
            
        Returns:
            更新后的支付记录，如果查询失败返回None
        """
        payment = await self.query_payment(payment_no)
        if not payment:
            return None
        
        # 如果已经是成功状态，直接返回
        if payment.status in ('paid', 'completed'):
            return payment
        
        # 主动查询支付宝
        alipay_result = await self.query_alipay_trade(payment_no)
        
        if not alipay_result:
            logger.info(f"[SyncStatus] 支付宝查询失败或未配置，保持本地状态 | payment_no={payment_no}, status={payment.status}")
            return payment
        
        trade_status = alipay_result.get("trade_status")
        
        # 调试：打印 trade_status 的类型和值
        logger.info(f"[SyncStatus] 调试 | payment_no={payment_no}, trade_status={repr(trade_status)}, alipay_result={alipay_result}")
        
        # 处理支付宝返回的状态
        # 注意：TRADE_HAS_SUCCESS 是沙箱环境返回的"已付款"状态
        if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED", "TRADE_HAS_SUCCESS"):
            # 支付宝已支付，但异步回调没到，手动更新状态
            logger.info(f"[SyncStatus] 支付宝已支付，同步更新状态 | payment_no={payment_no}, trade_status={trade_status}")
            
            payer_info = {
                "buyer_email": alipay_result.get("buyer_logon_id", ""),
                "buyer_id": alipay_result.get("buyer_id", ""),
                "pay_time": alipay_result.get("gmt_payment", ""),
                "sync_source": "alipay_query",  # 标记为同步查询来源
            }
            
            await self.handle_payment_callback(
                payment_no=payment_no,
                transaction_id=alipay_result.get("trade_no", ""),
                status="success",
                payer_info=payer_info,
                raw_data=alipay_result,
            )
            
            # 重新查询获取最新状态
            payment = await self.query_payment(payment_no)
        
        elif trade_status == "WAIT_BUYER_PAY":
            # 等待买家付款
            logger.info(f"[SyncStatus] 等待买家付款 | payment_no={payment_no}")
        
        elif trade_status in ("TRADE_CLOSED", "TRADE_CANCEL"):
            # 交易关闭/取消
            logger.info(f"[SyncStatus] 交易已关闭 | payment_no={payment_no}, trade_status={trade_status}")
            payment.status = "cancelled"
            await self.db.commit()
        
        return payment
    
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
        payment_no: str = None,
        order_no: str = None,
        transaction_id: str = "",
        status: str = "",
        payer_info: dict = None,
        raw_data: dict = None,
    ) -> bool:
        """
        处理支付回调
        
        Args:
            payment_no: 支付单号（可选，用于内部查询）
            order_no: 商户订单号（支付宝回调时使用 out_trade_no）
            transaction_id: 第三方交易号
            status: 支付状态 (success/failed)
            payer_info: 支付人信息
            raw_data: 原始回调数据
            
        Returns:
            是否处理成功
        """
        # 根据 order_no 或 payment_no 查询支付记录
        # 支付宝回调时使用 order_no（out_trade_no）
        if order_no:
            payment = await self.query_payment_by_order(order_no)
        elif payment_no:
            payment = await self.query_payment(payment_no)
        else:
            raise ValidationError("必须提供 payment_no 或 order_no")
        
        if not payment:
            raise NotFoundError(f"支付记录不存在 (order_no={order_no}, payment_no={payment_no})")
        
        if payment.status == "completed":
            # 已成功，跳过
            return True
        
        if payment.status == "processing":
            # 有其他处理正在执行（回调和轮询同时到达）
            # 等待其他处理完成，然后返回最终状态
            for _ in range(20):  # 最多等待2秒
                await asyncio.sleep(0.1)
                await self.db.refresh(payment)
                if payment.status in ("completed", "failed"):
                    logger.info(f"[handle_payment_callback] 等待其他处理完成，payment_no={payment_no}, 最终状态={payment.status}")
                    return True
                if payment.status == "pending":
                    # 其他处理失败或回滚了，继续处理
                    break
            
            # 等待超时，如果状态仍是 processing，说明其他处理卡住了
            # 此时不应该继续处理，否则会导致双重执行
            if payment.status == "processing":
                logger.warning(f"[handle_payment_callback] 等待超时，payment_no={payment_no} 正在被其他请求处理中")
                raise PaymentError(f"支付处理中，请稍后查询状态")
        
        if payment.status != "pending":
            # 其他异常状态，跳过
            return True
        
        # 先将状态更新为 processing，防止并发回调和轮询同时处理
        payment.status = "processing"
        payment.callback_status = "processing"
        payment.transaction_id = transaction_id or payment.transaction_id
        payment.payer_info = json.dumps(payer_info) if payer_info else payment.payer_info
        await self.db.commit()
        await self.db.refresh(payment)
        
        try:
            # 更新支付状态
            if status == "success":
                payment.status = "completed"
                payment.pay_time = datetime.now(timezone.utc)
                
                # 扣除余额并发放套餐
                await self._process_successful_payment(payment)
            else:
                payment.status = "failed"
            
            payment.callback_status = "processed"
            payment.callback_response = json.dumps(raw_data) if raw_data else None
            
            await self.db.commit()
        except Exception as e:
            logger.error(f"[handle_payment_callback] 处理失败，回滚状态: {e}")
            await self.db.rollback()
            payment.status = "pending"
            payment.callback_status = "failed"
            await self.db.commit()
            raise
        
        return True
    
    async def update_user_balance_after_payment(self, payment_no: str) -> bool:
        """
        【V8.0 新增】在查询支付状态时更新用户余额
        用于解决：模拟支付直接更新为 completed 状态时，不会触发回调，导致余额未增加的问题
        
        Args:
            payment_no: 支付单号
            
        Returns:
            是否成功更新余额
        """
        logger = get_logger("payment")
        logger.info(f"[UpdateBalance] 开始更新余额 | payment_no={payment_no}")
        
        # 查询支付记录
        payment = await self.query_payment(payment_no)
        if not payment:
            logger.warning(f"[UpdateBalance] 支付记录不存在 | payment_no={payment_no}")
            return False
        
        # 只有 completed 状态才处理（避免重复处理）
        if payment.status != "completed":
            logger.info(f"[UpdateBalance] 支付状态不是 completed，跳过 | payment_no={payment_no}, status={payment.status}")
            return False
        
        # 检查是否已经处理过（通过 transaction_id 判断）
        if payment.transaction_id and "processed:" in (payment.transaction_id or ""):
            logger.info(f"[UpdateBalance] 已经处理过，跳过 | payment_no={payment_no}")
            return False
        
        # 调用 _process_successful_payment 处理余额增加和账单创建
        try:
            await self._process_successful_payment(payment)
            logger.info(f"[UpdateBalance] 余额更新成功 | payment_no={payment_no}")
            return True
        except Exception as e:
            logger.error(f"[UpdateBalance] 余额更新失败 | payment_no={payment_no}, error={str(e)}")
            return False
    
    async def _process_successful_payment(self, payment: Payment) -> None:
        """
        处理成功支付的逻辑：增加账户余额
        
        Args:
            payment: 支付记录
            
        Note:
            此方法会检查是否已处理过，避免重复创建账单记录
        """
        from src.services.account_service import AccountService
        from src.config.settings import settings
        
        logger = get_logger("payment")
        
        # 【关键检查】检查是否已处理过（通过检查是否有对应的账单记录）
        from src.models.billing import Bill
        existing_bill = await self.db.execute(
            select(Bill).where(Bill.source_id == str(payment.id))
        )
        if existing_bill.scalar_one_or_none():
            logger.info(f"[_ProcessPayment] 支付已处理过，跳过 | payment_no={payment.payment_no}")
            return
        
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
        
        # 生成唯一的事务ID（用于标记已处理）
        processed_tx_id = f"processed:{payment.transaction_id or 'none'}"
        
        # 更新账户余额（account_service.add_balance 内部已创建 Bill）
        account_service = AccountService(self.db)
        await account_service.add_balance(
            user_id=str(payment.user_id),
            amount=total_amount,
            source_type="recharge",
            source_id=str(payment.id),
            description=description,
            transaction_id=processed_tx_id,  # 使用带标记的事务ID
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
            user.updated_at = datetime.now(timezone.utc)
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
        if payment_method == "alipay":
            # 调用支付宝生成真实支付链接
            payment_url = await self._generate_alipay_url(payment, None)
        else:
            payment_url = f"https://pay.example.com/custom?order_no={order_no}&amount={amount}"
        
        return payment, payment_url
