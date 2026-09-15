# -*- coding: utf-8 -*-
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    user='api_user',
    password='api_password',
    database='api_platform'
)
conn.autocommit = True
cur = conn.cursor()

# 查找 test9 用户
print('=== Looking for test9 user ===')
cur.execute("SELECT id, email, role, user_type, username FROM users WHERE email LIKE '%test9%' OR username LIKE '%test9%' ORDER BY created_at DESC")
users = cur.fetchall()
for row in users:
    print(f'id={row[0]}, email={row[1]}, role={row[2]}, user_type={row[3]}, username={row[4]}')

if users:
    user_id = users[0][0]
    print(f'\n=== Account for test9 ({user_id}) ===')
    cur.execute("SELECT id, user_id, balance, account_type, total_recharge FROM accounts WHERE user_id = %s", (user_id,))
    for row in cur.fetchall():
        print(f'id={row[0]}, user_id={row[1]}, balance={row[2]}, account_type={row[3]}, total_recharge={row[4]}')
    
    print(f'\n=== Bills for test9 ({user_id}) ===')
    cur.execute("SELECT bill_no, amount, balance_after, status, created_at FROM bills WHERE user_id = %s ORDER BY created_at DESC LIMIT 10", (user_id,))
    for row in cur.fetchall():
        print(f'bill_no={row[0]}, amount={row[1]}, balance_after={row[2]}, status={row[3]}, created_at={row[4]}')
    
    print(f'\n=== Payments for test9 ({user_id}) ===')
    cur.execute("SELECT payment_no, amount, status, pay_time, created_at FROM payments WHERE user_id = %s ORDER BY created_at DESC LIMIT 10", (user_id,))
    for row in cur.fetchall():
        print(f'payment_no={row[0]}, amount={row[1]}, status={row[2]}, pay_time={row[3]}, created_at={row[4]}')
else:
    print('No test9 user found')
    print('\n=== All recent users ===')
    cur.execute("SELECT id, email, role, user_type, username FROM users ORDER BY created_at DESC LIMIT 10")
    for row in cur.fetchall():
        print(f'id={row[0]}, email={row[1]}, role={row[2]}, user_type={row[3]}, username={row[4]}')

conn.close()
