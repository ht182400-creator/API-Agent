"""
Migration script to add request_params and tester columns to api_call_logs table
Usage: python -m scripts.migrate_add_request_params_tester
"""

import psycopg2
from src.config.settings import settings
from urllib.parse import urlparse


def migrate():
    """Add request_params and tester columns to api_call_logs table"""
    
    alter_table_sql = """
    -- 添加 request_params 列（JSON字符串格式的请求参数）
    ALTER TABLE api_call_logs 
    ADD COLUMN IF NOT EXISTS request_params TEXT;

    -- 添加 tester 列（测试人员用户名）
    ALTER TABLE api_call_logs 
    ADD COLUMN IF NOT EXISTS tester VARCHAR(100);

    -- 添加 request_id 列（全链路追踪ID）
    ALTER TABLE api_call_logs 
    ADD COLUMN IF NOT EXISTS request_id VARCHAR(64);

    -- 添加 request_path 列
    ALTER TABLE api_call_logs 
    ADD COLUMN IF NOT EXISTS request_path VARCHAR(500);

    -- 添加 request_method 列
    ALTER TABLE api_call_logs 
    ADD COLUMN IF NOT EXISTS request_method VARCHAR(10);

    -- 添加索引（如果不存在）
    CREATE INDEX IF NOT EXISTS idx_api_call_logs_request_id ON api_call_logs(request_id);
    """
    
    # Parse database URL
    db_url = settings.database_url
    result = urlparse(db_url)
    
    conn = psycopg2.connect(
        host=result.hostname,
        port=result.port or 5432,
        database=result.path.lstrip('/'),
        user=result.username,
        password=result.password
    )
    
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(alter_table_sql)
                print("[OK] api_call_logs table columns added successfully!")
                print("   - request_params (TEXT)")
                print("   - tester (VARCHAR(100))")
                print("   - request_id (VARCHAR(64))")
                print("   - request_path (VARCHAR(500))")
                print("   - request_method (VARCHAR(10))")
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
