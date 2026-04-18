"""更新现有用户数据"""
import psycopg2

conn = psycopg2.connect(
    host='localhost', 
    port=5432, 
    dbname='api_platform', 
    user='api_user', 
    password='api_password'
)
cur = conn.cursor()

# 更新现有用户
cur.execute("""
    UPDATE users 
    SET username = split_part(email, '@', 1),
        role = CASE 
            WHEN user_type = 'admin' THEN 'admin'
            WHEN user_type = 'owner' THEN 'developer'
            ELSE 'user'
        END,
        permissions = CASE
            WHEN user_type = 'admin' THEN '["*"]'::jsonb
            WHEN user_type = 'owner' THEN '["user:read", "user:write", "api:read", "api:write", "repo:manage"]'::jsonb
            WHEN user_type = 'developer' THEN '["user:read", "user:write", "api:read", "api:write"]'::jsonb
            ELSE '["user:read"]'::jsonb
        END
    WHERE username IS NULL
""")
conn.commit()

# 显示更新后的用户
cur.execute('SELECT username, email, user_type, role FROM users')
print('\n=== 当前用户列表 ===')
for row in cur.fetchall():
    print(f'  username: {row[0]:15} | email: {row[1]:25} | type: {row[2]:10} | role: {row[3]}')

cur.close()
conn.close()
print('\nDone!')
