"""测试 Analytics API"""
import httpx
import json

BASE_URL = "http://localhost:8000/api/v1"


def test_analytics():
    # 登录 owner 账户
    login_data = {
        "username": "owner",
        "password": "owner123"
    }

    print("=== 登录 Owner 账户 ===")
    resp = httpx.post(f"{BASE_URL}/auth/login", json=login_data, timeout=10)
    print(f"Login status: {resp.status_code}")
    print(f"Login response: {resp.text[:500]}")

    data = resp.json()
    print(f"Parsed data: {json.dumps(data, indent=2)[:500]}")

    # 检查 data 字段是否被正确提取
    if "data" in data:
        token = data["data"].get("access_token")
    else:
        token = data.get("access_token")

    if not token:
        print("ERROR: No access token found!")
        return

    print(f"\nGot token: {token[:40]}...")

    headers = {"Authorization": f"Bearer {token}"}

    # 测试各个 analytics 端点
    endpoints = [
        "/owner/overview",
        "/owner/sources",
        "/owner/weekly",
        "/owner/hourly",
    ]

    for endpoint in endpoints:
        print(f"\n=== Testing {endpoint} ===")
        try:
            resp = httpx.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text[:1500]}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    test_analytics()
