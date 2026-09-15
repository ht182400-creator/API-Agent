#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""将 PKCS8 私钥转换为 PKCS1 格式"""
import sys
sys.path.insert(0, '.')

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# 读取 PKCS8 私钥
with open('keys/alipay_private_key.pem', 'r') as f:
    pkcs8_key = f.read()

# 加载私钥
private_key = serialization.load_pem_private_key(
    pkcs8_key.encode(),
    password=None,
    backend=default_backend()
)

# 转换为 PKCS1 (传统 PEM 格式)
pkcs1_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
)

# 保存
with open('keys/alipay_private_key_pkcs1.pem', 'wb') as f:
    f.write(pkcs1_pem)

print("转换完成！")
print("新文件: keys/alipay_private_key_pkcs1.pem")
print("\n内容预览:")
print(pkcs1_pem.decode()[:100])
