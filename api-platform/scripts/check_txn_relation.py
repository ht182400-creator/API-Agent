import psycopg2
conn = psycopg2.connect('postgresql://api_user:api_password@localhost:5432/api_platform')
cur = conn.cursor()

# 检查 payments 表有哪些字段
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'payments' ORDER BY ordinal_position")
print('Payments 表字段:', [r[0] for r in cur.fetchall()])

# 检查 bills 表有哪些字段  
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'bills' ORDER BY ordinal_position")
print('Bills 表字段:', [r[0] for r in cur.fetchall()])

# 检查充值账单和支付记录的关联
cur.execute('''
    SELECT b.id, b.bill_no, b.transaction_id, b.amount, p.id as payment_id, p.payment_no, p.order_no
    FROM bills b
    LEFT JOIN payments p ON p.payment_no = b.transaction_id OR p.order_no = b.transaction_id
    WHERE b.bill_type = 'recharge'
    LIMIT 5
''')
print()
print('Bills 与 Payments 关联检查:')
for row in cur.fetchall():
    print(f'  Bill: id={row[0]}, txn_id={row[2]}, payment_id={row[4]}, payment_no={row[5]}, trade_no={row[6]}')

cur.close()
conn.close()
