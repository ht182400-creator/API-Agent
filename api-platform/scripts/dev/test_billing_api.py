import asyncio
import httpx
from datetime import datetime, timedelta

async def test():
    # 先登录获取 token
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # 登录
        login_resp = await client.post("/api/v1/auth/login", json={
            "username": "test19@test19.com",
            "password": "password123"
        })
        
        if login_resp.status_code != 200:
            print(f"登录失败: {login_resp.status_code}")
            print(login_resp.text)
            return
        
        token = login_resp.json()["data"]["access_token"]
        print(f"登录成功: {token[:50]}...")
        
        # 调用账单接口
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/v1/billing/bills", headers=headers, params={
            "page": 1,
            "page_size": 20,
            "start_date": "2026-05-08",
            "end_date": "2026-05-08"
        })
        
        print(f"\n账单接口响应状态: {resp.status_code}")
        data = resp.json()
        
        if data.get("code") == 0:
            items = data["data"]["items"]
            pagination = data["data"]["pagination"]
            print(f"总数: {pagination['total']}")
            print(f"返回记录数: {len(items)}")
            print("\n返回的记录:")
            for item in items:
                print(f"  ID={item['id']}, type={item['bill_type']}, amount={item['amount']}, time={item['created_at']}")
        else:
            print(f"错误: {data}")

asyncio.run(test())
