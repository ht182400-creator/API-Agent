import psycopg2
conn = psycopg2.connect('postgresql://api_user:api_password@localhost:5432/api_platform')
cur = conn.cursor()

# 查看充值账单和支付的关联
cur.execute('''
    SELECT 
        b.id, b.bill_no, b.amount, b.transaction_id as bill_txn,
        p.id as payment_id, p.payment_no, p.transaction_id as pay_txn
    FROM bills b
    LEFT JOIN payments p ON p.id = b.source_id::uuid
    WHERE b.bill_type = 'recharge' AND b.source_type = 'recharge'
    LIMIT 10
''')
print('Bills 与 Payments 关联 (source_id):')
for row in cur.fetchall():
    print(f'  Bill: id={row[0]}, bill_txn={row[3]}, payment_id={row[4]}, payment_no={row[5]}, pay_txn={row[6]}')

# 统计
cur.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN b.transaction_id IS NOT NULL THEN 1 END) as with_txn,
        COUNT(CASE WHEN p.transaction_id IS NOT NULL THEN 1 END) as pay_with_txn
    FROM bills b
    LEFT JOIN payments p ON p.id = b.source_id::uuid
    WHERE b.bill_type = 'recharge' AND b.source_type = 'recharge'
""")
row = cur.fetchone()
print(f'\n统计: total={row[0]}, bill_with_txn={row[1]}, payment_with_txn={row[2]}')

cur.close()
conn.close()
