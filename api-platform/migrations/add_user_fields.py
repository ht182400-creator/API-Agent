"""
数据库迁移脚本：添加 username、role、permissions 字段
=====================================================

迁移说明：
  - 添加 username 字段：支持用户名登录
  - 添加 role 字段：定义用户角色
  - 添加 permissions 字段：细粒度权限控制

角色与权限映射：
  - user_type='admin'  -> role='admin',     permissions=['*']
  - user_type='owner'   -> role='developer', permissions=['user:read', 'user:write', 'api:read', 'api:write', 'repo:manage']
  - user_type='developer' -> role='user',    permissions=['user:read', 'user:write', 'api:read', 'api:write']
  - user_type='user'    -> role='user',      permissions=['user:read']

使用方法：
  python migrations/add_user_fields.py
"""

import psycopg2

def migrate():
    conn = psycopg2.connect(
        host='localhost', 
        port=5432, 
        dbname='api_platform', 
        user='api_user', 
        password='api_password'
    )
    cur = conn.cursor()
    
    # 1. 添加 username 字段
    try:
        cur.execute('ALTER TABLE users ADD COLUMN username VARCHAR(50) UNIQUE')
        conn.commit()
        print('[OK] username field added')
    except Exception as e:
        conn.rollback()
        if 'already exists' in str(e):
            print('[SKIP] username field already exists')
        else:
            print(f'[ERROR] username field: {e}')
    
    # 2. 添加 role 字段
    try:
        cur.execute("""
            ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'
        """)
        conn.commit()
        print('[OK] role field added')
    except Exception as e:
        conn.rollback()
        if 'already exists' in str(e):
            print('[SKIP] role field already exists')
        else:
            print(f'[ERROR] role field: {e}')
    
    # 3. 添加 permissions 字段
    try:
        cur.execute("ALTER TABLE users ADD COLUMN permissions JSONB DEFAULT '[]'::jsonb")
        conn.commit()
        print('[OK] permissions field added')
    except Exception as e:
        conn.rollback()
        if 'already exists' in str(e):
            print('[SKIP] permissions field already exists')
        else:
            print(f'[ERROR] permissions field: {e}')
    
    # 4. 为现有用户设置 username 和默认权限
    try:
        # 设置 username = email.split('@')[0]
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
        print('[OK] Existing users updated')
        
        # 显示更新后的用户
        cur.execute('SELECT username, email, user_type, role FROM users')
        print('\n--- Current Users ---')
        for row in cur.fetchall():
            print(f'  {row[0]:15} | {row[1]:25} | {row[2]:10} -> role: {row[3]}')
        
    except Exception as e:
        conn.rollback()
        print(f'[ERROR] Update users: {e}')
    
    cur.close()
    conn.close()
    print('\nMigration completed!')

if __name__ == '__main__':
    migrate()
