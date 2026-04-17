"""初始化数据库和用户的脚本"""
import os
import sys

# 设置环境变量以解决 Windows 编码问题
os.environ['PGCLIENTENCODING'] = 'UTF8'
os.environ['PYTHONIOENCODING'] = 'utf-8'

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def init_database():
    # 连接到 PostgreSQL
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='postgres'
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # 检查并创建数据库
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'api_platform'")
    if not cur.fetchone():
        cur.execute('CREATE DATABASE api_platform')
        print('[OK] 数据库 api_platform 创建成功')
    else:
        print('[SKIP] 数据库 api_platform 已存在')

    # 检查并创建用户
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'api_user'")
    if not cur.fetchone():
        cur.execute("CREATE USER api_user WITH PASSWORD 'api_password'")
        print('[OK] 用户 api_user 创建成功')
    else:
        print('[SKIP] 用户 api_user 已存在')

    # 授予权限
    cur.execute('GRANT ALL PRIVILEGES ON DATABASE api_platform TO api_user')
    cur.execute('GRANT ALL ON SCHEMA public TO api_user')
    cur.execute('ALTER DATABASE api_platform OWNER TO api_user')
    
    conn.commit()
    cur.close()
    conn.close()
    print('[OK] 配置完成')
    print('')
    print('数据库连接信息:')
    print('  主机: localhost')
    print('  端口: 5432')
    print('  数据库: api_platform')
    print('  用户名: api_user')
    print('  密码: api_password')

if __name__ == '__main__':
    init_database()
