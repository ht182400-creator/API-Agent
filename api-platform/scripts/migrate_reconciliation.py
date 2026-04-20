"""
Reconciliation system database migration script

Creates platform_accounts, reconciliation_records, and reconciliation_disputes tables
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.config.database import AsyncSessionLocal


async def create_tables():
    """Create reconciliation tables"""
    
    async with AsyncSessionLocal() as db:
        try:
            # Create platform_accounts table
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS platform_accounts (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    channel VARCHAR(20) NOT NULL,
                    account_type VARCHAR(20) NOT NULL DEFAULT 'income',
                    account_no VARCHAR(100),
                    account_name VARCHAR(100),
                    balance DECIMAL(20, 2) DEFAULT 0.00,
                    currency VARCHAR(10) DEFAULT 'CNY',
                    status VARCHAR(20) DEFAULT 'active',
                    remark TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            print("[OK] platform_accounts table created")

            # Create index
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_platform_accounts_channel 
                ON platform_accounts(channel)
            """))
            print("[OK] platform_accounts index created")

            # Create reconciliation_records table
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS reconciliation_records (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    reconcile_date TIMESTAMPTZ NOT NULL,
                    channel VARCHAR(20) NOT NULL,
                    platform_trade_count VARCHAR(20) DEFAULT '0',
                    platform_trade_amount DECIMAL(20, 2) DEFAULT 0.00,
                    channel_trade_count VARCHAR(20) DEFAULT '0',
                    channel_trade_amount DECIMAL(20, 2) DEFAULT 0.00,
                    match_count VARCHAR(20) DEFAULT '0',
                    match_amount DECIMAL(20, 2) DEFAULT 0.00,
                    long_count VARCHAR(20) DEFAULT '0',
                    long_amount DECIMAL(20, 2) DEFAULT 0.00,
                    short_count VARCHAR(20) DEFAULT '0',
                    short_amount DECIMAL(20, 2) DEFAULT 0.00,
                    amount_diff_count VARCHAR(20) DEFAULT '0',
                    amount_diff_total DECIMAL(20, 2) DEFAULT 0.00,
                    status VARCHAR(20) DEFAULT 'pending',
                    bill_file_path VARCHAR(500),
                    bill_content TEXT,
                    completed_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            print("[OK] reconciliation_records table created")

            # Create indexes
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_recon_records_date 
                ON reconciliation_records(reconcile_date)
            """))
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_recon_records_channel 
                ON reconciliation_records(channel)
            """))
            await db.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_recon_records_date_channel 
                ON reconciliation_records(reconcile_date, channel)
            """))
            print("[OK] reconciliation_records indexes created")

            # Create reconciliation_disputes table
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS reconciliation_disputes (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    reconciliation_id UUID,
                    dispute_type VARCHAR(20) NOT NULL,
                    local_order_no VARCHAR(100),
                    channel_trade_no VARCHAR(100),
                    local_amount DECIMAL(20, 2),
                    channel_amount DECIMAL(20, 2),
                    diff_amount DECIMAL(20, 2),
                    reason VARCHAR(500),
                    handle_status VARCHAR(20) DEFAULT 'pending',
                    handle_remark TEXT,
                    handler_id UUID,
                    handled_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            print("[OK] reconciliation_disputes table created")

            # Create indexes
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_disputes_recon_id 
                ON reconciliation_disputes(reconciliation_id)
            """))
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_disputes_status 
                ON reconciliation_disputes(handle_status)
            """))
            print("[OK] reconciliation_disputes indexes created")

            # Insert default platform accounts
            await db.execute(text("""
                INSERT INTO platform_accounts (channel, account_type, account_name, balance, currency, status)
                VALUES 
                    ('alipay', 'income', 'Alipay Main Account', 0.00, 'CNY', 'active'),
                    ('wechat', 'income', 'WeChat Pay Account', 0.00, 'CNY', 'active'),
                    ('bankcard', 'income', 'Bank Card Account', 0.00, 'CNY', 'active')
                ON CONFLICT DO NOTHING
            """))
            print("[OK] Default platform accounts inserted")

            await db.commit()
            print("\nMigration completed successfully!")

        except Exception as e:
            await db.rollback()
            print(f"[ERROR] Migration failed: {e}")
            raise


async def main():
    print("Starting reconciliation database migration...")
    print("=" * 50)
    await create_tables()
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
