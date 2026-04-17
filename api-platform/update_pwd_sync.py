#!/usr/bin/env python3
"""同步方式更新用户密码为bcrypt格式"""

import sys
import os
sys.path.insert(0, '.')

# 设置编码
os.environ['PGCLIENTENCODING'] = 'utf8'

import psycopg2
from src.core.security import hash_password

def update_passwords():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="api_platform",
        user="api_user",
        password="api_password"
    )
    conn.set_client_encoding('UTF8')
    cursor = conn.cursor()
    
    # 更新所有用户的密码
    users_to_update = [
        ('admin@example.com', 'admin123'),
        ('owner@example.com', 'owner123'),
        ('developer@example.com', 'dev123456'),
        ('test@example.com', 'test123'),
    ]
    
    for email, password in users_to_update:
        hashed = hash_password(password)
        print(f"Updating {email}:")
        print(f"  New hash: {hashed[:60]}...")
        
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE email = %s",
            (hashed, email)
        )
    
    conn.commit()
    print("\nAll passwords updated!")
    
    # 验证更新
    cursor.execute("SELECT email, password_hash FROM users LIMIT 5")
    rows = cursor.fetchall()
    print("\nVerification:")
    for row in rows:
        print(f"  {row[0]}: {row[1][:60]}...")
    
    cursor.close()
    conn.close()

update_passwords()
