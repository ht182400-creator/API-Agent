# -*- coding: utf-8 -*-
import os
import psycopg2

os.environ['PGPASSWORD'] = 'api_password'

try:
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        user='api_user',
        password='api_password',
        database='api_platform',
        client_encoding='UTF8'
    )
    conn.autocommit = True
    cur = conn.cursor()

    print('=== Payment Callbacks ===')
    cur.execute("SELECT * FROM payment_callbacks ORDER BY created_at DESC LIMIT 20")
    cols = [desc[0] for desc in cur.description]
    print(f'Columns: {cols}')
    for row in cur.fetchall():
        print(row)

    print()
    print('=== test7 Payments callback_status ===')
    cur.execute("SELECT payment_no, status, callback_status, callback_response FROM payments WHERE user_id = '98c93f1d-3176-4478-8d8d-cb2f275443ba' ORDER BY created_at DESC")
    for row in cur.fetchall():
        print(f'payment_no={row[0]}, status={row[1]}, callback_status={row[2]}, response={row[3]}')

    conn.close()
except Exception as e:
    print(f'Error: {e}')
