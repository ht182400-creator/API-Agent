#!/usr/bin/env python3
"""查看所有用户"""

import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="api_platform",
    user="api_user",
    password="api_password"
)
cursor = conn.cursor()

cursor.execute("SELECT id, email, user_type FROM users LIMIT 10")
rows = cursor.fetchall()
print(f"Total users: {len(rows)}")
for row in rows:
    print(f"  {row}")

cursor.close()
conn.close()
