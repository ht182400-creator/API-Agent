#!/usr/bin/env python3
"""
今日调用次数功能测试脚本
测试目标：验证API调用能被正确记录和统计

使用说明：
1. 先确保后端服务运行在 http://localhost:8000
2. 确保数据库中有测试账户 owner@example.com 和 developer@example.com
3. 确保有一个已上线的仓库
4. 运行本脚本执行完整测试流程
"""

import requests
import json
import time
import sys
from typing import Optional, Dict, Any

# 配置
BASE_URL = "http://localhost:8000/api/v1"
TEST_TIMEOUT = 30

# 测试账户
OWNER_EMAIL = "owner@example.com"
OWNER_PASSWORD = "owner123456"
DEV_EMAIL = "developer@example.com"
DEV_PASSWORD = "dev123456"


class APIClient:
    """简化版API客户端"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.token: Optional[str] = None
    
    def set_token(self, token: str):
        self.token = token
    
    def request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        response = self.session.request(
            method=method,
            url=url,
            headers=headers,
            timeout=TEST_TIMEOUT,
            **kwargs
        )
        
        if response.status_code >= 400:
            print(f"请求失败: {response.status_code}")
            print(f"响应: {response.text}")
            raise Exception(f"API请求失败: {response.status_code}")
        
        return response.json()
    
    def get(self, path: str, **kwargs) -> Dict[str, Any]:
        return self.request("GET", path, **kwargs)
    
    def post(self, path: str, **kwargs) -> Dict[str, Any]:
        return self.request("POST", path, **kwargs)
    
    def put(self, path: str, **kwargs) -> Dict[str, Any]:
        return self.request("PUT", path, **kwargs)


def print_section(title: str):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_step(step_num: int, description: str):
    """打印步骤标题"""
    print(f"\n>>> 步骤{step_num}: {description}")


def main():
    print_section("今日调用次数功能测试")
    
    client = APIClient(BASE_URL)
    
    # ========== 步骤1: Owner登录 ==========
    print_step(1, "Owner账户登录")
    try:
        response = client.post("/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        if response.get("code") == 0:
            owner_token = response["data"]["access_token"]
            owner_user = response["data"]["user"]
            client.set_token(owner_token)
            print(f"✓ Owner登录成功: {owner_user['email']} ({owner_user['user_type']})")
        else:
            print(f"✗ Owner登录失败: {response}")
            return
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return
    
    # ========== 步骤2: 获取仓库列表 ==========
    print_step(2, "获取Owner的仓库列表")
    try:
        response = client.get("/repositories/my")
        if response.get("code") == 0:
            repos = response["data"]["items"]
            if not repos:
                print("✗ 没有找到仓库，请先创建仓库")
                return
            # 选择第一个在线仓库
            online_repos = [r for r in repos if r["status"] == "online"]
            if online_repos:
                repo = online_repos[0]
            else:
                repo = repos[0]
            
            repo_id = repo["id"]
            repo_slug = repo["slug"]
            print(f"✓ 找到仓库: {repo['name']} (状态: {repo['status']})")
            print(f"  ID: {repo_id}")
            print(f"  Slug: {repo_slug}")
        else:
            print(f"✗ 获取仓库列表失败: {response}")
            return
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return
    
    # ========== 步骤3: 查看初始调用统计 ==========
    print_step(3, "查看调用前统计（基准值）")
    try:
        response = client.get(f"/repositories/{repo_id}/stats")
        if response.get("code") == 0:
            stats_before = response["data"]
            today_calls_before = stats_before.get("today_calls", 0)
            total_calls_before = stats_before.get("total_calls", 0)
            print(f"✓ 当前统计:")
            print(f"  今日调用: {today_calls_before}")
            print(f"  总调用量: {total_calls_before}")
        else:
            print(f"! 获取统计失败（可能返回模拟数据）: {response}")
            today_calls_before = 0
            total_calls_before = 0
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        today_calls_before = 0
        total_calls_before = 0
    
    # ========== 步骤4: Developer登录 ==========
    print_step(4, "Developer账户登录")
    try:
        dev_client = APIClient(BASE_URL)
        response = dev_client.post("/auth/login", json={
            "email": DEV_EMAIL,
            "password": DEV_PASSWORD
        })
        if response.get("code") == 0:
            dev_token = response["data"]["access_token"]
            dev_client.set_token(dev_token)
            print(f"✓ Developer登录成功: {response['data']['user']['email']}")
        else:
            print(f"✗ Developer登录失败: {response}")
            return
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return
    
    # ========== 步骤5: 创建API Key ==========
    print_step(5, "创建API Key用于测试")
    try:
        response = dev_client.post("/quota/keys", json={
            "name": f"测试Key_{int(time.time())}",
            "auth_type": "api_key",
            "daily_quota": 10000,
            "monthly_quota": 300000
        })
        if response.get("code") == 0:
            api_key_data = response["data"]
            api_key = api_key_data["api_key"]
            api_key_id = api_key_data["id"]
            print(f"✓ API Key创建成功")
            print(f"  Key ID: {api_key_id}")
            print(f"  Key: {api_key[:20]}...")
        else:
            print(f"✗ API Key创建失败: {response}")
            return
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return
    
    # ========== 步骤6: 执行API调用 ==========
    print_step(6, "执行3次真实API调用")
    
    # 由于当前后端的chat接口是模拟的，我们需要使用简化的调用方式
    # 直接调用仓库的chat端点
    
    for i in range(1, 4):
        try:
            # 构造请求头
            headers = {
                "Content-Type": "application/json",
                "X-Access-Key": api_key,
                "X-Timestamp": str(int(time.time() * 1000)),
                "X-Nonce": f"nonce_{int(time.time() * 1000)}_{i}"
            }
            
            # 生成简单的HMAC签名（如果需要）
            # 这里简化处理，直接调用
            response = requests.post(
                f"{BASE_URL}/repositories/{repo_slug}/chat",
                headers=headers,
                json={"message": f"测试消息 {i}"},
                timeout=TEST_TIMEOUT
            )
            
            result = response.json()
            if result.get("code") == 0:
                print(f"  第{i}次调用成功: {result['data'].get('answer', 'N/A')[:30]}...")
            else:
                print(f"  第{i}次调用失败: {result}")
            
            time.sleep(1)  # 间隔1秒
            
        except Exception as e:
            print(f"  第{i}次调用异常: {e}")
    
    print("✓ API调用完成")
    
    # ========== 步骤7: 再次查看调用统计 ==========
    print_step(7, "查看调用后统计（验证增加）")
    try:
        response = client.get(f"/repositories/{repo_id}/stats")
        if response.get("code") == 0:
            stats_after = response["data"]
            today_calls_after = stats_after.get("today_calls", 0)
            total_calls_after = stats_after.get("total_calls", 0)
            print(f"✓ 调用后统计:")
            print(f"  今日调用: {today_calls_after} (变化: +{today_calls_after - today_calls_before})")
            print(f"  总调用量: {total_calls_after} (变化: +{total_calls_after - total_calls_before})")
            
            if today_calls_after > today_calls_before:
                print("\n🎉 测试成功！调用次数已正确记录！")
            else:
                print("\n⚠️ 警告：调用次数未增加，可能统计接口返回的是模拟数据")
                print("   请检查数据库 api_call_logs 表是否有新记录")
        else:
            print(f"! 获取统计失败: {response}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    # ========== 步骤8: 查看调用日志 ==========
    print_step(8, "查看调用日志")
    try:
        response = dev_client.get("/quota/logs", params={"page_size": 10})
        if response.get("code") == 0:
            logs = response["data"]["items"]
            print(f"✓ 找到 {len(logs)} 条调用日志")
            for log in logs[:3]:
                print(f"  - {log.get('endpoint', 'N/A')} | {log.get('method', 'N/A')} | "
                      f"状态:{log.get('response_status', 'N/A')} | {log.get('created_at', 'N/A')[:19]}")
        else:
            print(f"! 获取日志失败: {response}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    # ========== 测试总结 ==========
    print_section("测试总结")
    print(f"""
测试完成！

如果测试成功，你应该看到：
1. Owner能够登录并获取仓库列表
2. Developer能够创建API Key
3. API调用能够成功执行
4. 调用统计显示调用次数增加

注意事项：
- 如果"调用后统计"没有增加，说明 get_repository_stats 接口返回的是模拟数据
- 请检查 api_call_logs 表是否有新的记录
- 如果没有日志记录，说明调用没有被正确记录

下一步：
- 查看数据库：SELECT * FROM api_call_logs ORDER BY created_at DESC LIMIT 10;
- 修改 get_repository_stats 实现真实查询
""")


if __name__ == "__main__":
    main()
