"""
数据库迁移脚本 V2.13
功能：为 api_call_logs 表添加 request_id 字段

问题背景：
  - 日志页面显示的"请求ID"实际是 APICallLog 表的自增 id，不是真正的请求追踪ID
  - middleware.py 中生成的 request_id (UUID) 未被保存到数据库
  - 导致无法追踪单个请求的全链路

解决方案：
  1. 在 APICallLog 表添加 request_id 字段 (String(64), nullable, indexed)
  2. repositories.py 中记录日志时保存 request_id
  3. quota.py 日志接口返回 request_id
  4. 前端展示 request_id

执行时间：2026-04-22
"""

import os
import sys
import psycopg2
from psycopg2 import sql

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import settings


def get_db_connection():
    """获取数据库连接"""
    from urllib.parse import urlparse
    
    # 使用 urllib 正确解析 URL
    db_url = settings.database_url
    parsed = urlparse(db_url)
    
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip('/'),
        user=parsed.username,
        password=parsed.password
    )


def upgrade():
    """添加 request_id 字段"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查字段是否已存在
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'api_call_logs' AND column_name = 'request_id'
        """)
        
        if cursor.fetchone():
            print("字段 request_id 已存在，跳过迁移")
            return
        
        # 添加字段
        cursor.execute("""
            ALTER TABLE api_call_logs 
            ADD COLUMN request_id VARCHAR(64)
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX idx_api_call_logs_request_id 
            ON api_call_logs(request_id)
        """)
        
        conn.commit()
        print("迁移成功：已添加 request_id 字段到 api_call_logs 表")
        
    except Exception as e:
        conn.rollback()
        print(f"迁移失败：{e}")
        raise
    finally:
        cursor.close()
        conn.close()


def downgrade():
    """删除 request_id 字段"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            ALTER TABLE api_call_logs DROP COLUMN IF EXISTS request_id
        """)
        conn.commit()
        print("回滚成功：已删除 request_id 字段")
        
    except Exception as e:
        conn.rollback()
        print(f"回滚失败：{e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库迁移脚本')
    parser.add_argument('action', choices=['upgrade', 'downgrade'], 
                        help='执行的操作: upgrade(升级) 或 downgrade(回滚)')
    args = parser.parse_args()
    
    if args.action == 'upgrade':
        upgrade()
    else:
        downgrade()
