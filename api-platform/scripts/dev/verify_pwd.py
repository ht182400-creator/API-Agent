#!/usr/bin/env python3
"""独立密码验证测试"""

import sys
sys.path.insert(0, '.')

from src.core.security import hash_password, verify_password

# 测试密码
password = 'admin123'

# 生成新哈希
new_hash = hash_password(password)
print(f"New bcrypt hash: {new_hash}")
print(f"Starts with $2: {new_hash.startswith('$2')}")

# 测试SHA256哈希
import hashlib
sha256_hash = hashlib.sha256(password.encode()).hexdigest()
print(f"\nSHA256 hash: {sha256_hash}")
print(f"Starts with $2: {sha256_hash.startswith('$2')}")

# 验证
print(f"\nVerify with bcrypt: {verify_password(password, new_hash)}")
print(f"Verify with SHA256: {verify_password(password, sha256_hash)}")
