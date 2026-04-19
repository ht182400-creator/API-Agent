#!/usr/bin/env python
"""手动产生API调用记录的脚本"""
import requests
import time
import hashlib
import base64
import hmac
import uuid

BASE_URL = 'http://localhost:8000/api/v1'

# 1. 登录
r = requests.post(f'{BASE_URL}/auth/login', json={
    'email': 'developer@example.com',
    'password': 'dev123456'
})
t = r.json()['data']['access_token']
headers = {'Authorization': f'Bearer {t}'}
print('Login OK')

# 2. 获取仓库
r2 = requests.get(f'{BASE_URL}/repositories', headers=headers)
repos = r2.json()['data']['items']
if not repos:
    print('No repos found')
    exit(1)
repo_slug = repos[0]['slug']
print(f'Repo: {repo_slug}')

# 3. 获取API Key
r3 = requests.get(f'{BASE_URL}/quota/keys', headers=headers)
keys = r3.json()['data']['items']
if not keys:
    print('No keys found')
    exit(1)

# 4. 获取完整key
key_uuid = keys[0]['id']
r4 = requests.get(f'{BASE_URL}/quota/keys/{key_uuid}/reveal', headers=headers)
full_key = r4.json()['data']['api_key']
print(f'Full Key: {full_key[:20]}...')

# 5. 执行5次API调用
for i in range(5):
    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())
    message = f'{full_key}{timestamp}{nonce}'
    signature = base64.b64encode(
        hmac.new(full_key.encode(), message.encode(), hashlib.sha256).digest()
    ).decode()
    
    r5 = requests.post(
        f'{BASE_URL}/repositories/{repo_slug}/chat',
        json={'message': f'Test call {i+1}'},
        headers={
            'X-Access-Key': full_key,
            'X-Timestamp': timestamp,
            'X-Signature': signature,
            'X-Nonce': nonce,
        }
    )
    print(f'Call {i+1}: status={r5.status_code}')

print('\nDone! Refresh page to see today_calls updated.')
