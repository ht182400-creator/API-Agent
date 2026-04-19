# 今日调用次数功能测试案例

## 测试目标
验证"今日调用次数"功能的完整数据流，确保API调用能被正确记录和统计。

## 测试环境准备

### 1. 确认服务运行状态
确保后端服务正在运行：
```bash
cd d:/Work_Area/AI/API-Agent/api-platform
# 启动后端服务（如果未启动）
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 确认数据库中有测试数据
确保存在以下测试账户：
| 角色 | 用户名 | 邮箱 | 密码 |
|------|--------|------|------|
| owner | owner | owner@example.com | owner123456 |
| developer | developer | developer@example.com | dev123456 |

---

## 测试步骤

### 步骤1：获取Access Token（认证）

使用 owner 账户登录获取token：
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@example.com",
    "password": "owner123456"
  }'
```

**预期响应：**
```json
{
  "code": 0,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGc...",
    "user": {
      "id": "...",
      "email": "owner@example.com",
      "user_type": "owner"
    }
  }
}
```

记录返回的 `access_token`。

---

### 步骤2：获取仓库列表

用 owner 的 token 获取自己创建的仓库：
```bash
curl -X GET "http://localhost:8000/api/v1/repositories/my" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**预期响应：**
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "仓库UUID",
        "name": "psychology-api",
        "slug": "psychology-api",
        "status": "online",
        ...
      }
    ],
    "pagination": {...}
  }
}
```

记录一个在线仓库的 `id` 和 `slug`。

---

### 步骤3：创建API Key（使用developer账户）

使用developer账户登录并创建API Key：
```bash
# 1. 获取developer的token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "developer@example.com",
    "password": "dev123456"
  }'
```

然后创建API Key：
```bash
curl -X POST "http://localhost:8000/api/v1/quota/keys" \
  -H "Authorization: Bearer <DEVELOPER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试Key",
    "auth_type": "api_key",
    "daily_quota": 10000,
    "monthly_quota": 300000
  }'
```

**预期响应：**
```json
{
  "code": 0,
  "data": {
    "id": "API_KEY_ID",
    "key_name": "测试Key",
    "api_key": "sk_xxxx_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "status": "active",
    ...
  }
}
```

**重要**：记录返回的完整 `api_key` 值（创建时才会返回完整key）。

---

### 步骤4：检查当前调用统计（调用前）

查看仓库当前的调用统计：
```bash
curl -X GET "http://localhost:8000/api/v1/repositories/<REPO_ID>/stats" \
  -H "Authorization: Bearer <OWNER_TOKEN>"
```

**预期响应：**
```json
{
  "code": 0,
  "data": {
    "repo_id": "...",
    "total_calls": 0,
    "today_calls": 0,
    "week_calls": 0,
    "total_cost": 0.0,
    ...
  }
}
```

记录当前的 `today_calls` 值（应该为0或之前的数值）。

---

### 步骤5：执行真实API调用（触发调用日志）

使用刚才创建的API Key发起真实的API调用：
```bash
curl -X POST "http://localhost:8000/api/v1/repositories/<REPO_SLUG>/chat" \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: <API_KEY>" \
  -H "X-Signature: <HMAC_SIGNATURE>" \
  -H "X-Timestamp: <TIMESTAMP>" \
  -H "X-Nonce: <NONCE>" \
  -d '{
    "message": "你好，我今天心情不好"
  }'
```

**或者使用Python SDK（推荐）：**

创建测试脚本 `test_api_call.py`：

```python
#!/usr/bin/env python3
"""
今日调用次数测试 - 使用Python SDK发起真实API调用
"""
import sys
sys.path.insert(0, 'd:/Work_Area/AI/API-Agent/api-platform/sdk/python')

from api_platform import Client
import time

# 配置
API_KEY = "sk_xxxx_xxxxxxxxxxxxxxxxxxxx"  # 步骤3创建的API Key
API_SECRET = "xxxxxxxxxxxxxxxxxxxxxxxx"   # 步骤3创建的Secret
BASE_URL = "http://localhost:8000/api/v1"
REPO_SLUG = "psychology-api"  # 替换为实际的仓库slug

def main():
    # 初始化客户端
    client = Client(
        api_key=API_KEY,
        api_secret=API_SECRET,
        base_url=BASE_URL,
        log_level="DEBUG"
    )
    
    print("=" * 50)
    print("开始测试API调用统计功能")
    print("=" * 50)
    
    # 发起3次API调用
    messages = [
        "你好，我今天心情不好",
        "有什么方法可以放松吗？",
        "谢谢你的建议"
    ]
    
    for i, msg in enumerate(messages, 1):
        print(f"\n>>> 第 {i} 次调用...")
        try:
            response = client.psychology.psychology_api.chat(
                message=msg,
                user_id="test_user_001"
            )
            print(f"响应: {response.answer[:50]}...")
            print(f"请求ID: {response.request_id}")
        except Exception as e:
            print(f"调用失败: {e}")
        
        # 每次调用间隔1秒
        time.sleep(1)
    
    print("\n" + "=" * 50)
    print("API调用完成，已发送3次请求")
    print("=" * 50)

if __name__ == "__main__":
    main()
```

运行测试脚本：
```bash
cd d:/Work_Area/AI/API-Agent/api-platform
python test_api_call.py
```

**预期输出：**
```
==================================================
开始测试API调用统计功能
==================================================

>>> 第 1 次调用...
响应: 这是一个模拟的回答。在生产环境中...
请求ID: abc123...

>>> 第 2 次调用...
响应: 这是一个模拟的回答。在生产环境中...
请求ID: def456...

>>> 第 3 次调用...
响应: 这是一个模拟的回答。在生产环境中...
请求ID: ghi789...

==================================================
API调用完成，已发送3次请求
==================================================
```

---

### 步骤6：验证调用次数增加（调用后）

再次查看仓库统计：
```bash
curl -X GET "http://localhost:8000/api/v1/repositories/<REPO_ID>/stats" \
  -H "Authorization: Bearer <OWNER_TOKEN>"
```

**预期响应：**
```json
{
  "code": 0,
  "data": {
    "repo_id": "...",
    "total_calls": 3,
    "today_calls": 3,
    "week_calls": 3,
    ...
  }
}
```

对比步骤4的值，`today_calls` 应该增加了3次。

---

### 步骤7：查看调用日志（数据库层面验证）

通过API查看调用日志：
```bash
curl -X GET "http://localhost:8000/api/v1/quota/logs" \
  -H "Authorization: Bearer <DEVELOPER_TOKEN>"
```

**预期响应：**
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "日志ID",
        "api_key_id": "API_KEY_ID",
        "endpoint": "chat",
        "method": "POST",
        "response_status": 200,
        "created_at": "2026-04-19T23:45:00"
      },
      ...
    ],
    "pagination": {...}
  }
}
```

---

### 步骤8：查看数据库记录（可选，高级验证）

直接查询数据库验证：

```sql
-- 查看今日调用日志
SELECT 
    id,
    repo_id,
    api_key_id,
    endpoint,
    method,
    status_code,
    created_at
FROM api_call_logs
WHERE DATE(created_at) = CURRENT_DATE
ORDER BY created_at DESC;

-- 按仓库统计今日调用次数
SELECT 
    repo_id,
    COUNT(*) as today_calls
FROM api_call_logs
WHERE DATE(created_at) = CURRENT_DATE
GROUP BY repo_id;
```

---

## 测试验证清单

| 验证项 | 预期结果 | 实际结果 | 通过 |
|--------|----------|----------|------|
| Owner能成功登录获取token | 返回有效token | | |
| Owner能查看自己的仓库列表 | 返回仓库数据 | | |
| Developer能创建API Key | 返回完整key和secret | | |
| 调用前today_calls值为X | 显示正确数值 | | |
| 执行3次API调用成功 | 返回200响应 | | |
| 调用后today_calls值为X+3 | 数值增加3 | | |
| 调用日志中能看到3条记录 | 日志完整 | | |

---

## 常见问题排查

### 问题1：调用返回401未授权
**原因**：API Key无效或已过期
**解决**：
1. 检查API Key是否正确
2. 检查API Key状态是否为active
3. 检查HMAC签名是否正确

### 问题2：调用返回403禁止
**原因**：没有权限访问该仓库
**解决**：
1. 检查仓库是否上线（status=online）
2. 检查API Key是否有权限访问该仓库

### 问题3：today_calls没有增加
**原因**：
1. 统计接口返回的是模拟数据（当前代码中stats接口是mock的）
2. 调用日志没有正确写入数据库

**解决**：
1. 检查`api_call_logs`表是否有新记录
2. 检查`RepoService.call_repository`方法中的`_log_api_call`调用
3. 检查后端日志是否有错误信息

### 问题4：仓库统计返回全0
**原因**：`get_repository_stats`接口返回的是模拟数据
**解决**：
需要修改后端代码，将`get_repository_stats`改为从`api_call_logs`表查询真实数据。

---

## 代码改进建议

当前`get_repository_stats`返回的是模拟数据（全是0），需要修改为真实查询：

```python
# 文件：api-platform/src/api/v1/repositories.py
# 修改 get_repository_stats 方法

@router.get("/{repo_id}/stats", response_model=BaseResponse[dict])
async def get_repository_stats(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: "User" = Depends(get_current_user),
):
    from src.models.billing import APICallLog
    from datetime import datetime, timedelta
    
    # 查找仓库...
    # 权限检查...
    
    today = datetime.utcnow().date()
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    # 今日调用量（真实查询）
    today_result = await db.execute(
        select(func.count(APICallLog.id)).where(
            and_(
                APICallLog.repo_id == uuid.UUID(repo_id),
                func.date(APICallLog.created_at) == today,
            )
        )
    )
    today_calls = today_result.scalar()
    
    # 本周调用量
    week_result = await db.execute(
        select(func.count(APICallLog.id)).where(
            and_(
                APICallLog.repo_id == uuid.UUID(repo_id),
                APICallLog.created_at >= week_ago,
            )
        )
    )
    week_calls = week_result.scalar()
    
    # 总调用量
    total_result = await db.execute(
        select(func.count(APICallLog.id)).where(
            APICallLog.repo_id == uuid.UUID(repo_id)
        )
    )
    total_calls = total_result.scalar()
    
    return BaseResponse(
        data={
            "repo_id": str(repo.id),
            "total_calls": total_calls or 0,
            "today_calls": today_calls or 0,
            "week_calls": week_calls or 0,
            "total_cost": 0.0,
            ...
        }
    )
```

---

## 测试完成

完成以上所有步骤后，你就完成了"今日调用次数"功能的完整测试。
测试结果应显示：
1. API调用能被正确执行
2. 调用日志被正确记录到数据库
3. 统计接口能从数据库读取真实的调用数据
4. Owner工作台能正确显示今日调用次数
