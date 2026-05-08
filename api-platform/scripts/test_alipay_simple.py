#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""简化版支付宝测试"""
import sys
import os
sys.path.insert(0, '.')

from src.config.settings import settings

# 读取 PKCS1 格式私钥
with open('keys/alipay_private_key_pkcs1.pem', 'r') as f:
    private_key_content = f.read()

print("=" * 50)
print("支付宝配置")
print("=" * 50)
print(f"AppID: {settings.alipay_app_id}")
print(f"网关: {settings.alipay_sandbox_gateway}")
print(f"私钥格式: {private_key_content[:50]}...")

try:
    from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
    from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
    from alipay.aop.api.request.AlipayTradePagePayRequest import AlipayTradePagePayRequest
    from alipay.aop.api.domain.AlipayTradePagePayModel import AlipayTradePagePayModel
    
    # 创建配置
    alipay_client_config = AlipayClientConfig()
    alipay_client_config.app_id = settings.alipay_app_id
    alipay_client_config.app_private_key = private_key_content
    alipay_client_config.alipay_public_key = settings.get_alipay_public_key()
    alipay_client_config.server_url = settings.alipay_sandbox_gateway
    alipay_client_config.sign_type = "RSA2"
    
    client = DefaultAlipayClient(alipay_client_config)
    
    # 创建请求模型
    model = AlipayTradePagePayModel()
    model.out_trade_no = "TEST20260107_001"
    model.total_amount = "0.01"
    model.subject = "测试充值"
    model.product_code = "FAST_INSTANT_TRADE_PAY"
    
    request = AlipayTradePagePayRequest(biz_model=model)
    request.return_url = "http://localhost:3000/recharge"
    
    # 获取表单
    form = client.page_execute(request, http_method="GET")
    
    print("\n" + "=" * 50)
    print("结果")
    print("=" * 50)
    
    if "sign fail" in str(form).lower():
        print("[FAIL] 签名失败")
    elif form.startswith("http"):
        print(f"[OK] 支付链接: {form[:100]}...")
    else:
        print(f"[OK] 表单响应 (前200字符): {form[:200]}")
        
except Exception as e:
    print(f"\n[FAIL] Error: {e}")
    import traceback
    traceback.print_exc()
