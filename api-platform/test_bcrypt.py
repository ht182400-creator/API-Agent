#!/usr/bin/env python3
"""测试密码哈希兼容性"""

import sys
sys.path.insert(0, '.')

# 直接测试 bcrypt
try:
    import bcrypt
    password = b'admin123'
    hashed = bcrypt.hashpw(password, bcrypt.gensalt())
    print(f"bcrypt hash: {hashed}")
    print(f"Verify: {bcrypt.checkpw(password, hashed)}")
except Exception as e:
    print(f"bcrypt error: {e}")

# 测试 passlib
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    password = 'admin123'
    hashed = pwd_context.hash(password)
    print(f"\npasslib bcrypt hash: {hashed}")
    print(f"Verify: {pwd_context.verify(password, hashed)}")
except Exception as e:
    print(f"passlib error: {e}")
