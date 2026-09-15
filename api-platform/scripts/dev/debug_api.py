import asyncio
import httpx
import json

async def test():
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        # 尝试登录
        login_data = {
            "username": "test19@test19.com",
            "password": "Test123456"  # 尝试常见密码
        }
        
        try:
            resp = await client.post("/api/v1/auth/login", json=login_data)
            print(f"登录响应: {resp.status_code}")
            if resp.status_code == 200:
                token = resp.json()["data"]["access_token"]
                print(f"Token: {token[:50]}...")
                
                # 调用账单接口
                headers = {"Authorization": f"Bearer {token}"}
                bills_resp = await client.get("/api/v1/billing/bills", headers=headers, params={
                    "page": 1,
                    "page_size": 20,
                    "start_date": "2026-05-08",
                    "end_date": "2026-05-08"
                })
                
                print(f"\n账单接口: {bills_resp.status_code}")
                data = bills_resp.json()
                if data.get("code") == 0:
                    print(f"总数: {data['data']['pagination']['total']}")
                    print(f"返回: {len(data['data']['items'])} 条")
                    for item in data['data']['items']:
                        print(f"  {item['id']}: {item['bill_type']} {item['amount']} {item['created_at']}")
                else:
                    print(f"错误: {data}")
            else:
                print(f"登录失败: {resp.text}")
        except Exception as e:
            print(f"错误: {e}")

asyncio.run(test())
