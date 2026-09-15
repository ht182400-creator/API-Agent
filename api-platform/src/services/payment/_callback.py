"""
支付回调：回调入账（幂等）、余额更新、充值后用户升级

由 `scripts/dev/split_payment_service.py` 从 `payment_service.py` 精确搬移生成，
方法体与原实现逐字一致（仅移动位置）。

⚠️ 依赖宿主类提供 ``self.db``（由 :class:`PaymentService` 组合）。
"""

import asyncio
import json
from datetime import datetime, timezone
from sqlalchemy import select
from src.models.payment import Payment
from src.models.billing import Bill
from src.core.exceptions import ValidationError, NotFoundError, PaymentError
from src.config.logging_config import get_logger

logger = get_logger("payment")


class PaymentCallbackMixin:
    """支付回调：回调入账（幂等）、余额更新、充值后用户升级"""

    
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
