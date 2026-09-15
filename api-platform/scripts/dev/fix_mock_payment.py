# -*- coding: utf-8 -*-
"""
修复脚本：在模拟支付模式下，创建订单时直接完成支付

问题：模拟支付环境下，支付回调没有正确处理，导致余额不增加
解决方案：在模拟支付模式下，创建订单时就直接完成支付
"""

import re

# 读取文件
with open('src/services/payment_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 create_payment 方法并修改
old_create_payment = '''    async def create_payment(
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
        
        return payment, payment_url'''

new_create_payment = '''    async def create_payment(
        self,
        user_id: str,
        package_id: str,
        payment_method: str = "alipay",
        callback_url: str = None,
        description: str = None,
    ) -> Tuple[Payment, str]:
        """
        创建支付订单
        
        【V4.0 修复】模拟支付模式下直接完成支付流程
        
        Args:
            user_id: 用户ID
            package_id: 套餐ID
            payment_method: 支付方式 (alipay/wechat/paypal)
            callback_url: 回调通知地址
            description: 订单描述
            
        Returns:
            (Payment对象, 支付跳转URL或二维码链接)
        """
        from src.config.settings import settings
        
        # 获取套餐信息
        package = await self.get_package(package_id)
        if not package:
            raise NotFoundError("套餐不存在")
        
        if package.is_active != "true":
            raise ValidationError("套餐已下架")
        
        # 生成订单号
        order_no = self.generate_order_no()
        payment_no = self.generate_payment_no()
        
        # 【修复】判断是否为模拟支付模式
        is_mock_mode = getattr(settings, 'payment_mock_mode', True)
        
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
            status="completed" if is_mock_mode else "pending",  # 模拟模式直接完成
            callback_url=callback_url,
            description=description or f"充值{package.name}",
            pay_time=datetime.utcnow() if is_mock_mode else None,
            transaction_id=f"MOCK_{payment_no}" if is_mock_mode else None,
        )
        
        self.db.add(payment)
        await self.db.flush()  # 先 flush，获取 payment.id 用于后续处理
        
        # 【模拟支付模式】直接完成支付，增加余额
        if is_mock_mode:
            logger = get_logger("payment")
            logger.info(f"[CreatePayment-MOCK] 模拟支付模式，直接完成充值: payment_no={payment_no}, user_id={user_id}")
            
            # 直接处理成功支付逻辑
            try:
                await self._process_successful_payment(payment)
                logger.info(f"[CreatePayment-MOCK] 模拟支付成功: payment_no={payment_no}")
            except Exception as e:
                logger.error(f"[CreatePayment-MOCK] 模拟支付失败: payment_no={payment_no}, error={e}", exc_info=True)
                payment.status = "failed"
                payment.remark = f"模拟支付处理失败: {str(e)}"
        
        await self.db.commit()
        await self.db.refresh(payment)
        
        # 生成支付链接（模拟实现）
        payment_url = await self._generate_payment_url(payment, package, payment_method)
        
        return payment, payment_url'''

if old_create_payment in content:
    content = content.replace(old_create_payment, new_create_payment)
    print('SUCCESS: create_payment method updated')
else:
    print('ERROR: old_create_payment not found')
    # 尝试找到方法
    if 'async def create_payment' in content:
        print('Method found, but pattern does not match exactly')
        start = content.find('async def create_payment')
        end = content.find('\n    async def ', start + 10)
        print('Current method snippet:')
        print(content[start:end][:500])
    else:
        print('Method not found at all')

# 写入文件
with open('src/services/payment_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
