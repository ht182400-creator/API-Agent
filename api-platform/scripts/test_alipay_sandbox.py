#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
支付宝沙箱环境测试脚本
"""
import sys
import os

# 修复Windows编码问题
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import settings

print("=" * 50)
print("支付宝配置检查")
print("=" * 50)

# 检查配置
print(f"\n1. AppID: {settings.alipay_app_id}")
print(f"2. 沙箱模式: {settings.alipay_sandbox}")
print(f"3. 网关地址: {settings.alipay_sandbox_gateway if settings.alipay_sandbox else settings.alipay_production_gateway}")

# 检查私钥
private_key = settings.get_alipay_private_key()
if private_key:
    print(f"4. 私钥长度: {len(private_key)} 字符")
    print(f"   私钥格式: {private_key[:40]}...")
else:
    print("4. 私钥: 未找到!")

# 检查公钥
public_key = settings.get_alipay_public_key()
if public_key:
    print(f"5. 公钥长度: {len(public_key)} 字符")
    print(f"   公钥格式: {public_key[:40]}...")
else:
    print("5. 公钥: 未找到!")

print(f"\n6. 回调地址: {settings.alipay_notify_url}")
print(f"7. 返回地址: {settings.alipay_return_url}")

# 测试 SDK 连接
print("\n" + "=" * 50)
print("SDK 连接测试")
print("=" * 50)

try:
    from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
    from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
    from alipay.aop.api.request.AlipayTradePagePayRequest import AlipayTradePagePayRequest
    
    # 读取 PKCS1 格式私钥
    with open('keys/alipay_private_key_pkcs1.pem', 'r') as f:
        private_key_content = f.read()
    
    # 配置客户端
    alipay_client_config = AlipayClientConfig()
    alipay_client_config.app_id = settings.alipay_app_id
    alipay_client_config.app_private_key = private_key_content
    alipay_client_config.alipay_public_key = settings.get_alipay_public_key()
    alipay_client_config.server_url = settings.alipay_sandbox_gateway if settings.alipay_sandbox else settings.alipay_production_gateway
    
    print(f"\nSDK 版本信息:")
    print(f"  AlipayClientConfig 属性: {dir(alipay_client_config)}")
    
    # 创建客户端
    client = DefaultAlipayClient(alipay_client_config)
    print("[OK] 客户端创建成功")
    
    # 创建测试请求
    request = AlipayTradePagePayRequest()
    request.biz_content = {
        "out_trade_no": "TEST_20260101_001",
        "total_amount": "0.01",
        "subject": "测试支付",
        "product_code": "FAST_INSTANT_TRADE_PAY",
    }
    request.return_url = settings.alipay_return_url
    request.notify_url = settings.alipay_notify_url
    
    # 执行请求
    print("\n执行支付请求...")
    response = client.execute(request)
    
    print(f"\n响应类型: {type(response)}")
    print(f"响应内容: {response}")
    
    if isinstance(response, dict):
        print(f"\n响应Keys: {response.keys()}")
        if "alipay_trade_page_pay_response" in response:
            pay_response = response["alipay_trade_page_pay_response"]
            print(f"支付响应: {pay_response}")
            if "code" in pay_response:
                print(f"响应码: {pay_response['code']}")
                print(f"响应消息: {pay_response.get('msg', 'N/A')}")
                if pay_response.get('sub_msg'):
                    print(f"子消息: {pay_response['sub_msg']}")
    elif isinstance(response, str):
        print(f"\n响应是字符串 (可能是HTML表单)")
        if response.startswith("http"):
            print(f"[OK] 支付链接: {response}")
        elif "sign fail" in response.lower():
            print("[FAIL] 签名失败!")
        else:
            print(f"前100字符: {response[:100]}")
    else:
        print(f"响应类型: {type(response)}")
        
except Exception as e:
    print(f"\n[FAIL] Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
