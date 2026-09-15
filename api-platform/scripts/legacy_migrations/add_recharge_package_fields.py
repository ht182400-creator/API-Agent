"""
数据库迁移脚本：添加充值套餐金额限制字段
=========================================

迁移说明：
  - 添加 min_amount 字段：最小充值金额
  - 添加 max_amount 字段：最大充值金额
  - 添加 is_custom 字段：是否自定义金额套餐

使用方法：
  python migrations/add_recharge_package_fields.py
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

    # 1. 添加 min_amount 字段
    try:
        cur.execute('ALTER TABLE recharge_packages ADD COLUMN min_amount VARCHAR(20)')
        conn.commit()
        print('[OK] min_amount field added')
    except Exception as e:
        conn.rollback()
        if 'already exists' in str(e):
            print('[SKIP] min_amount field already exists')
        else:
            print(f'[ERROR] min_amount field: {e}')

    # 2. 添加 max_amount 字段
    try:
        cur.execute('ALTER TABLE recharge_packages ADD COLUMN max_amount VARCHAR(20)')
        conn.commit()
        print('[OK] max_amount field added')
    except Exception as e:
        conn.rollback()
        if 'already exists' in str(e):
            print('[SKIP] max_amount field already exists')
        else:
            print(f'[ERROR] max_amount field: {e}')

    # 3. 添加 is_custom 字段
    try:
        cur.execute("""
            ALTER TABLE recharge_packages ADD COLUMN is_custom VARCHAR(10) DEFAULT 'false'
        """)
        conn.commit()
        print('[OK] is_custom field added')
    except Exception as e:
        conn.rollback()
        if 'already exists' in str(e):
            print('[SKIP] is_custom field already exists')
        else:
            print(f'[ERROR] is_custom field: {e}')

    # 验证字段添加结果
    try:
        cur.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'recharge_packages'
            AND column_name IN ('min_amount', 'max_amount', 'is_custom')
        """)
        print('\n--- Recharge Package New Fields ---')
        for row in cur.fetchall():
            print(f'  {row[0]:15} | {row[1]:20} | default: {row[2]}')

        # 显示所有套餐
        cur.execute("""
            SELECT id, name, price, min_amount, max_amount, is_custom
            FROM recharge_packages
            ORDER BY sort_order
        """)
        print('\n--- Current Recharge Packages ---')
        for row in cur.fetchall():
            print(f'  {str(row[0])[:8]}: {row[1]} | {row[2]}元 | min:{row[3]} max:{row[4]} custom:{row[5]}')

    except Exception as e:
        print(f'[ERROR] Verification: {e}')

    cur.close()
    conn.close()
    print('\nMigration completed!')


if __name__ == '__main__':
    migrate()
