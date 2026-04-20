"""
计费配置表创建和初始化脚本

使用方法:
    python scripts/sql/create_pricing_configs_table.py       # 仅创建表
    python scripts/sql/create_pricing_configs_table.py --init  # 创建并初始化数据
    python scripts/sql/create_pricing_configs_table.py --drop  # 删除并重建
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from src.config.database import async_engine, AsyncSessionLocal


async def create_table():
    """创建表"""
    print("Creating pricing_configs table...")
    async with async_engine.begin() as conn:
        # 创建表
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pricing_configs (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                repo_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
                pricing_type VARCHAR(20) NOT NULL,
                price_per_call DECIMAL(10, 4),
                free_calls INTEGER DEFAULT 0,
                price_per_1k_input_tokens DECIMAL(10, 4),
                price_per_1k_output_tokens DECIMAL(10, 4),
                free_input_tokens INTEGER DEFAULT 0,
                free_output_tokens INTEGER DEFAULT 0,
                packages JSONB DEFAULT '[]'::jsonb,
                default_package_id VARCHAR(50),
                pricing_tiers JSONB DEFAULT '[]'::jsonb,
                vip_discounts JSONB DEFAULT '{}'::jsonb,
                priority INTEGER DEFAULT 100,
                valid_from TIMESTAMP,
                valid_until TIMESTAMP,
                status VARCHAR(20) DEFAULT 'active',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by UUID
            )
        """))
        # 创建索引
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pricing_configs_repo_id ON pricing_configs(repo_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pricing_configs_pricing_type ON pricing_configs(pricing_type)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pricing_configs_status ON pricing_configs(status)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pricing_configs_priority ON pricing_configs(priority)"))
        # 创建触发器函数
        await conn.execute(text("""
            CREATE OR REPLACE FUNCTION update_pricing_configs_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql'
        """))
        await conn.execute(text("DROP TRIGGER IF EXISTS update_pricing_configs_updated_at ON pricing_configs"))
        await conn.execute(text("CREATE TRIGGER update_pricing_configs_updated_at BEFORE UPDATE ON pricing_configs FOR EACH ROW EXECUTE FUNCTION update_pricing_configs_updated_at()"))
    print("Table created successfully!")


async def drop_table():
    """删除表"""
    print("Dropping pricing_configs table...")
    async with async_engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS pricing_configs CASCADE"))
    print("Table dropped!")


async def init_data():
    """初始化数据"""
    print("Inserting initial data...")
    async with async_engine.begin() as conn:
        # 按调用计费
        await conn.execute(text("""
            INSERT INTO pricing_configs (id, repo_id, pricing_type, price_per_call, free_calls, pricing_tiers, vip_discounts, priority, status, description, created_at)
            VALUES (
                'd0000001-0000-0000-0000-000000000001',
                NULL,
                'call',
                0.0100,
                0,
                '[{"min_calls": 0, "max_calls": 10000, "discount": 1.0}, {"min_calls": 10001, "max_calls": 100000, "discount": 0.95}, {"min_calls": 100001, "max_calls": null, "discount": 0.9}]'::jsonb,
                '{"0": 1.0, "1": 1.0, "2": 0.98, "3": 0.95}'::jsonb,
                100,
                'active',
                '全局默认按调用计费配置',
                CURRENT_TIMESTAMP
            ) ON CONFLICT DO NOTHING
        """))
        # 按Token计费
        await conn.execute(text("""
            INSERT INTO pricing_configs (id, repo_id, pricing_type, price_per_1k_input_tokens, price_per_1k_output_tokens, free_input_tokens, free_output_tokens, pricing_tiers, vip_discounts, priority, status, description, created_at)
            VALUES (
                'd0000001-0000-0000-0000-000000000002',
                NULL,
                'token',
                0.0030,
                0.0060,
                0, 0,
                '[{"min_calls": 0, "max_calls": 1000000, "discount": 1.0}, {"min_calls": 1000001, "max_calls": 10000000, "discount": 0.95}, {"min_calls": 10000001, "max_calls": null, "discount": 0.9}]'::jsonb,
                '{"0": 1.0, "1": 1.0, "2": 0.98, "3": 0.95}'::jsonb,
                100,
                'active',
                '全局默认按Token计费配置 (参考OpenAI GPT-4o)',
                CURRENT_TIMESTAMP
            ) ON CONFLICT DO NOTHING
        """))
        # 套餐包计费
        await conn.execute(text("""
            INSERT INTO pricing_configs (id, repo_id, pricing_type, packages, default_package_id, priority, status, description, created_at)
            VALUES (
                'd0000001-0000-0000-0000-000000000003',
                NULL,
                'package',
                '[{"id": "package_free", "name": "免费版", "calls": 100, "price": 0.00, "period_days": 30, "features": ["基础API调用", "100次/月"]}, {"id": "package_basic", "name": "基础版", "calls": 5000, "price": 29.90, "period_days": 30, "features": ["全部API调用", "5000次/月", "技术支持"]}, {"id": "package_pro", "name": "专业版", "calls": 50000, "price": 199.00, "period_days": 30, "features": ["全部API调用", "50000次/月", "优先支持", "统计报表"]}, {"id": "package_enterprise", "name": "企业版", "calls": 500000, "price": 999.00, "period_days": 30, "features": ["全部API调用", "500000次/月", "专属支持", "高级统计", "定制开发"]}]'::jsonb,
                'package_basic',
                100,
                'active',
                '全局默认套餐包计费配置',
                CURRENT_TIMESTAMP
            ) ON CONFLICT DO NOTHING
        """))
    print("Initial data inserted!")


async def verify():
    """验证"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT id, pricing_type, status, description FROM pricing_configs"))
        rows = result.fetchall()
        print(f"\nTotal records: {len(rows)}")
        for row in rows:
            print(f"  - {row[0]}: {row[1]} ({row[2]}) - {row[3]}")


async def main(mode: str):
    if mode == "drop":
        await drop_table()
        await create_table()
    elif mode == "init":
        await create_table()
        await init_data()
    else:
        await create_table()
    
    await verify()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="计费配置表管理脚本")
    parser.add_argument("--drop", action="store_true", help="删除并重建表")
    parser.add_argument("--init", action="store_true", help="创建并初始化数据")
    args = parser.parse_args()

    if args.drop:
        mode = "drop"
    elif args.init:
        mode = "init"
    else:
        mode = "create"

    asyncio.run(main(mode))
