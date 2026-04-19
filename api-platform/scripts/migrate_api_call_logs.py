"""
Migration script to add api_call_logs table
Usage: python -m scripts.migrate_api_call_logs
"""

import psycopg2
from src.config.settings import settings
from urllib.parse import urlparse


def migrate():
    """Create api_call_logs table"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS api_call_logs (
        id BIGSERIAL PRIMARY KEY,
        repo_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
        api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL,
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        endpoint VARCHAR(255),
        method VARCHAR(10),
        request_path VARCHAR(500),
        request_method VARCHAR(10),
        status_code BIGINT,
        response_time VARCHAR(20),
        tokens_used BIGINT DEFAULT 0,
        cost VARCHAR(20) DEFAULT '0',
        source VARCHAR(50),
        ip_address VARCHAR(50),
        user_agent VARCHAR(500),
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_api_call_logs_repo_id ON api_call_logs(repo_id);
    CREATE INDEX IF NOT EXISTS idx_api_call_logs_api_key_id ON api_call_logs(api_key_id);
    CREATE INDEX IF NOT EXISTS idx_api_call_logs_user_id ON api_call_logs(user_id);
    CREATE INDEX IF NOT EXISTS idx_api_call_logs_created_at ON api_call_logs(created_at);
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
                cur.execute(create_table_sql)
                print("✅ api_call_logs table created successfully!")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
