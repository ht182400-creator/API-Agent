#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PostgreSQL 数据库初始化脚本
使用 asyncpg 进行数据库设置
"""

import asyncio
import asyncpg
import sys

async def setup_database():
    params = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'postgres',
        'database': 'postgres',
        'timeout': 10
    }
    
    try:
        print('正在连接到 PostgreSQL...')
        conn = await asyncpg.connect(**params)
        print('连接成功！')
        
        # 获取版本
        version = await conn.fetchval('SELECT version()')
        print(f'Server: {version[:50]}...')
        
        # 检查数据库
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname='api_platform'"
        )
        if exists:
            print('[OK] 数据库 api_platform 已存在')
        else:
            await conn.execute('CREATE DATABASE api_platform')
            print('[OK] 数据库 api_platform 创建成功')
        
        await conn.close()
        
        # 连接到新数据库创建用户
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='api_platform',
            timeout=10
        )
        
        # 创建用户
        user_exists = await conn.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname='api_user'"
        )
        if not user_exists:
            await conn.execute(
                "CREATE USER api_user WITH PASSWORD 'api_password'"
            )
            print('[OK] 用户 api_user 创建成功')
        else:
            print('[OK] 用户 api_user 已存在')
        
        # 授予权限
        await conn.execute('GRANT ALL PRIVILEGES ON DATABASE api_platform TO api_user')
        await conn.execute('GRANT ALL ON SCHEMA public TO api_user')
        print('[OK] 权限配置完成')
        
        await conn.close()
        print('=' * 50)
        print('数据库设置完成！')
        return True
        
    except asyncpg.PostgresConnectionError as e:
        print(f'连接错误: {e}')
        return False
    except Exception as e:
        print(f'错误: {type(e).__name__}: {e}')
        return False

def main():
    success = asyncio.run(setup_database())
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
