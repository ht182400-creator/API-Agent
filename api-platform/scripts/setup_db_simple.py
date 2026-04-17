#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PostgreSQL 数据库初始化脚本
Windows 环境下的数据库设置
"""

import os
import sys

def setup_database():
    import psycopg2
    
    params = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'postgres',
        'dbname': 'postgres',
        'connect_timeout': 5,
        'sslmode': 'disable',
        'options': '-c client_encoding=UTF8'
    }
    
    try:
        print('正在连接到 PostgreSQL...')
        conn = psycopg2.connect(**params)
        print('连接成功！')
        
        cur = conn.cursor()
        cur.execute('SELECT version()')
        version = cur.fetchone()[0]
        print(f'Server: {version}')
        
        # 检查数据库
        cur.execute("SELECT datname FROM pg_database WHERE datname='api_platform'")
        if cur.fetchone():
            print('[OK] 数据库 api_platform 已存在')
        else:
            cur.execute('CREATE DATABASE api_platform')
            conn.commit()
            print('[OK] 数据库 api_platform 创建成功')
        
        # 创建用户
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname='api_user'")
        if not cur.fetchone():
            cur.execute("CREATE USER api_user WITH PASSWORD 'api_password'")
            print('[OK] 用户 api_user 创建成功')
        else:
            print('[OK] 用户 api_user 已存在')
        
        # 授予权限
        cur.execute('GRANT ALL PRIVILEGES ON DATABASE api_platform TO api_user')
        cur.execute('GRANT ALL ON SCHEMA public TO api_user')
        conn.commit()
        print('[OK] 权限配置完成')
        
        cur.close()
        conn.close()
        print('=' * 50)
        print('数据库设置完成！')
        return True
        
    except psycopg2.Error as e:
        print(f'PostgreSQL 错误: {e}')
        return False
    except Exception as e:
        print(f'错误: {type(e).__name__}: {e}')
        return False

if __name__ == '__main__':
    success = setup_database()
    sys.exit(0 if success else 1)
