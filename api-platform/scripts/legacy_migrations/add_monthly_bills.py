"""
月度账单表迁移脚本

创建 monthly_bills 表用于存储月度汇总账单
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.config.database import engine, AsyncSessionLocal


async def create_monthly_bills_table():
    """创建 monthly_bills 表"""
    
    create_table_sql = """
    -- 月度账单汇总表
    CREATE TABLE IF NOT EXISTS monthly_bills (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        
        -- 关联信息
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        
        -- 账单周期
        year BIGINT NOT NULL,
        month BIGINT NOT NULL,
        
        -- 环境标识
        environment VARCHAR(20) DEFAULT 'simulation',
        
        -- 账单统计
        total_recharge VARCHAR(20) DEFAULT '0',
        total_consumption VARCHAR(20) DEFAULT '0',
        net_change VARCHAR(20) DEFAULT '0',
        beginning_balance VARCHAR(20) DEFAULT '0',
        ending_balance VARCHAR(20) DEFAULT '0',
        
        -- 使用统计
        total_calls BIGINT DEFAULT 0,
        total_tokens BIGINT DEFAULT 0,
        
        -- 账单详情
        details TEXT,
        
        -- 状态
        status VARCHAR(20) DEFAULT 'pending',
        
        -- 审核信息
        reviewed_by UUID,
        reviewed_at TIMESTAMP,
        review_comment TEXT,
        
        -- 生成信息
        generated_by UUID,
        generated_at TIMESTAMP,
        
        -- 发布信息
        published_at TIMESTAMP,
        
        -- 审计字段
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # 创建索引
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_monthly_bills_user_id ON monthly_bills(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_monthly_bills_year_month ON monthly_bills(year, month);",
        "CREATE INDEX IF NOT EXISTS idx_monthly_bills_status ON monthly_bills(status);",
        "CREATE INDEX IF NOT EXISTS idx_monthly_bills_environment ON monthly_bills(environment);",
        "CREATE INDEX IF NOT EXISTS idx_monthly_bills_user_year_month ON monthly_bills(user_id, year, month);",
    ]
    
    async with AsyncSessionLocal() as session:
        try:
            # 创建表
            print("创建 monthly_bills 表...")
            await session.execute(text(create_table_sql))
            
            # 创建索引
            for idx_sql in create_indexes_sql:
                print(f"创建索引: {idx_sql[:50]}...")
                await session.execute(text(idx_sql))
            
            await session.commit()
            print("[OK] monthly_bills 表创建成功!")
            
        except Exception as e:
            await session.rollback()
            print(f"[ERROR] 创建表失败: {e}")
            raise


async def drop_monthly_bills_table():
    """删除 monthly_bills 表（用于回滚）"""
    
    async with AsyncSessionLocal() as session:
        try:
            print("删除 monthly_bills 表...")
            await session.execute(text("DROP TABLE IF EXISTS monthly_bills CASCADE;"))
            await session.commit()
            print("[OK] monthly_bills 表已删除!")
        except Exception as e:
            await session.rollback()
            print(f"[ERROR] 删除表失败: {e}")
            raise


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "down":
        print("执行回滚...")
        asyncio.run(drop_monthly_bills_table())
    else:
        print("执行迁移...")
        asyncio.run(create_monthly_bills_table())
        print("\n迁移完成!")
        print("使用方法:")
        print("  python add_monthly_bills.py      - 创建表")
        print("  python add_monthly_bills.py down - 回滚（删除表）")
