"""
支付宝对接：当面付下单、二维码生成/刷新、交易查询、支付状态同步

由 `scripts/dev/split_payment_service.py` 从 `payment_service.py` 精确搬移生成，
方法体与原实现逐字一致（仅移动位置）。

⚠️ 依赖宿主类提供 ``self.db``（由 :class:`PaymentService` 组合）。
"""

import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from src.models.payment import Payment, RechargePackage
from src.core.exceptions import ValidationError, NotFoundError, PaymentError
from src.config.logging_config import get_logger

logger = get_logger("payment")


class PaymentAlipayMixin:
    """支付宝对接：当面付下单、二维码生成/刷新、交易查询、支付状态同步"""

    
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
