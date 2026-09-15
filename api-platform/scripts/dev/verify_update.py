#!/usr/bin/env python3
"""验证数据库中的密码哈希"""

import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="api_platform",
    user="api_user",
    password="api_password"
)
cursor = conn.cursor()

cursor.execute("SELECT email, password_hash, LENGTH(password_hash) FROM users WHERE email = 'admin@example.com'")
row = cursor.fetchone()
if row:
    email, pwd_hash, length = row
    print(f"Email: {email}")
    print(f"Hash length: {length}")
    print(f"Hash starts with $2: {pwd_hash.startswith('$2')}")
    print(f"Hash: {pwd_hash}")
else:
    print("User not found")

cursor.close()
conn.close()
