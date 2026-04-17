import requests
import json

r = requests.post('http://localhost:8080/api/v1/auth/login', 
                  json={'email': 'admin@example.com', 'password': 'admin123'})
print('Status:', r.status_code)
print('Response:', r.text[:500])
