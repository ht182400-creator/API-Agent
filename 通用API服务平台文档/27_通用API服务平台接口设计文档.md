# 通用API服务平台 - 接口设计文档

## 文档信息

| 属性 | 内容 |
|------|------|
| **文档编号** | API-PLATFORM-2026-001 |
| **版本** | V1.7 |
| **日期** | 2026-04-19 |
| **更新说明** | V1.7: 新增管理员用户管理接口 /admin/users；修复用户更新接口使用JSON Body |

---

## 1. 接口概述

### 1.1 接口分类

| 类别 | 说明 | 认证方式 |
|------|------|----------|
| **开发者API** | 对外提供的API调用接口 | API Key / HMAC |
| **管理API** | 控制台后端接口 | JWT Token |
| **内部API** | 服务间调用接口 | 服务认证 |
| **Webhook** | 回调通知接口 | 签名验证 |

### 1.2 基础规范

| 规范 | 说明 |
|------|------|
| **协议** | HTTPS |
| **方法** | REST |
| **数据格式** | JSON |
| **字符编码** | UTF-8 |
| **版本** | URL路径 /v1/ |

---

## 2. 开发者API（对外）

### 2.1 认证接口

#### 2.1.1 签名生成

```yaml
接口: POST /v1/auth/signature
说明: 生成HMAC签名

请求头:
  X-Access-Key: <access_key>
  X-Timestamp: <timestamp_ms>
  X-Nonce: <random_string>
  Content-Type: application/json

请求体:
{
  "method": "POST",
  "path": "/v1/repositories/psychology/chat",
  "body_hash": "<sha256_hex>",
  "headers": {
    "X-Custom-Header": "value"
  }
}

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "signature": "xxxx",
    "expires_at": 1640000000000
  }
}
```

#### 2.1.2 Token刷新

```yaml
接口: POST /v1/auth/refresh
说明: 刷新JWT Token

请求头:
  Authorization: Bearer <refresh_token>

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "xxxx",
    "refresh_token": "xxxx",
    "expires_in": 3600
  }
}
```

### 2.2 仓库调用API

#### 2.2.1 通用调用

```yaml
接口: {METHOD} /v1/repositories/{repo_slug}/*
说明: 代理调用仓库API

请求头:
  X-Access-Key: <api_key>
  X-Signature: <hmac_signature>
  X-Timestamp: <timestamp>
  X-Nonce: <nonce>

请求示例:
  POST /v1/repositories/psychology/chat

请求体:
{
  "question": "我最近失眠怎么办？",
  "context": {
    "age": 30,
    "gender": "male"
  }
}

响应:
{
  "code": 0,
  "message": "success",
  "request_id": "req_xxxx",
  "data": {
    "answer": "建议您...",
    "suggestions": [...]
  },
  "usage": {
    "tokens": 150,
    "cost": 0.015
  }
}

错误响应:
{
  "code": 40001,
  "message": "Rate limit exceeded",
  "request_id": "req_xxxx",
  "details": {
    "limit": 1000,
    "remaining": 0,
    "reset_at": 1640000000
  }
}
```

#### 2.2.2 错误码定义

| 错误码 | 名称 | 说明 |
|--------|------|------|
| 0 | SUCCESS | 成功 |
| 40001 | BAD_REQUEST | 请求参数错误 |
| 40002 | INVALID_SIGNATURE | 签名无效 |
| 40003 | TIMESTAMP_EXPIRED | 时间戳过期 |
| 40101 | INVALID_CREDENTIALS | 用户名/邮箱或密码错误 |
| 40102 | TOKEN_EXPIRED | Token无效或已过期 |
| 40103 | KEY_DISABLED | Key已禁用 |
| 40104 | KEY_EXPIRED | Key已过期 |
| 40105 | INVALID_KEY | API Key无效 |
| 40301 | ACCESS_DENIED | 无权访问 |
| 40302 | REPO_NOT_ALLOWED | 未授权访问此仓库 |
| 40401 | REPO_NOT_FOUND | 仓库不存在 |
| 40402 | ENDPOINT_NOT_FOUND | 接口不存在 |
| 42901 | RATE_LIMIT_EXCEEDED | 请求过于频繁 |
| 42902 | QUOTA_EXCEEDED | 配额超限 |
| 50001 | INTERNAL_ERROR | 服务器内部错误 |
| 50301 | REPO_UNAVAILABLE | 仓库服务不可用 |
| 50302 | REPO_TIMEOUT | 仓库响应超时 |

### 2.3 仓库信息API

#### 2.3.1 仓库列表

```yaml
接口: GET /v1/repositories
说明: 获取可用仓库列表

查询参数:
  type: string, 仓库类型筛选
  protocol: string, 协议类型筛选
  page: int, 页码
  page_size: int, 每页数量

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "repo_xxx",
        "name": "psychology",
        "display_name": "心理问答",
        "description": "专业心理问答服务",
        "type": "psychology",
        "protocol": "http",
        "status": "online",
        "pricing": {
          "type": "token",
          "price_per_token": 0.001
        },
        "endpoints": [
          "/chat",
          "/assess"
        ]
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 50,
      "total_pages": 3
    }
  }
}
```

#### 2.3.2 仓库详情

```yaml
接口: GET /v1/repositories/{repo_slug}
说明: 获取仓库详情

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "repo_xxx",
    "name": "psychology",
    "display_name": "心理问答",
    "description": "...",
    "type": "psychology",
    "protocol": "http",
    "status": "online",
    "owner": {
      "id": "user_xxx",
      "name": "平台官方"
    },
    "pricing": {
      "type": "token",
      "price_per_token": 0.001,
      "free_tokens": 1000
    },
    "limits": {
      "rpm": 100,
      "rph": 1000,
      "daily": 10000
    },
    "endpoints": [
      {
        "path": "/chat",
        "method": "POST",
        "description": "智能问答",
        "params": {...}
      }
    ],
    "docs_url": "https://docs.example.com",
    "sla": {
      "uptime": 99.9,
      "latency_p99": 500
    }
  }
}
```

### 2.4 日志查询API

#### 2.4.1 调用日志

```yaml
接口: GET /v1/logs
说明: 查询API调用日志

请求头:
  X-Access-Key: <api_key>
  X-Signature: <signature>

查询参数:
  repo_id: string, 仓库ID
  start_time: timestamp, 开始时间
  end_time: timestamp, 结束时间
  status_code: int, 状态码
  page: int, 页码
  page_size: int, 每页数量

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "request_id": "req_xxx",
        "repo_id": "repo_xxx",
        "repo_name": "psychology",
        "endpoint": "/chat",
        "method": "POST",
        "status_code": 200,
        "latency_ms": 150,
        "tokens_used": 100,
        "cost": 0.01,
        "ip": "1.2.3.4",
        "created_at": "2026-04-16T10:00:00Z"
      }
    ],
    "pagination": {...}
  }
}
```

### 2.5 配额管理API（控制台）

#### 2.5.1 获取API Keys列表

```yaml
接口: GET /api/v1/quota/keys
说明: 获取当前用户的API Keys列表
认证: Bearer Token

查询参数:
  page: int, 页码，默认1
  page_size: int, 每页数量，默认20

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "uuid",
        "key_name": "生产环境Key",
        "key_prefix": "sk_live_xxxx",
        "status": "active",
        "auth_type": "api_key",
        "rate_limit_rpm": 1000,
        "rate_limit_rph": 10000,
        "daily_quota": 100000,
        "monthly_quota": null,
        "last_used_at": "2026-04-17T10:00:00",
        "created_at": "2026-04-01T10:00:00",
        "expires_at": null
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 5,
      "total_pages": 1
    }
  }
}
```

#### 2.5.2 创建API Key

```yaml
接口: POST /api/v1/quota/keys
说明: 创建新的API Key
认证: Bearer Token

请求体:
{
  "name": "测试Key",
  "auth_type": "api_key",
  "rate_limit_rpm": 1000,
  "rate_limit_rph": 10000,
  "daily_quota": null,
  "monthly_quota": null
}

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "uuid",
    "key_name": "测试Key",
    "key_prefix": "sk_test_xxxx",
    "api_key": "sk_test_xxxx_yyyy...",  // 仅创建时返回完整key
    "secret": "zzzz...",  // 仅创建时返回
    "status": "active",
    "created_at": "2026-04-18T10:00:00"
  }
}
```

#### 2.5.3 获取Key详情

```yaml
接口: GET /api/v1/quota/keys/{key_id}
说明: 获取API Key详情
认证: Bearer Token

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "uuid",
    "key_name": "生产环境Key",
    "key_prefix": "sk_live_xxxx",
    "status": "active",
    "auth_type": "api_key",
    "rate_limit_rpm": 1000,
    "rate_limit_rph": 10000,
    "daily_quota": 100000,
    "monthly_quota": null,
    "last_used_at": "2026-04-17T10:00:00",
    "created_at": "2026-04-01T10:00:00",
    "expires_at": null
  }
}
```

#### 2.5.4 更新API Key

```yaml
接口: PUT /api/v1/quota/keys/{key_id}
说明: 更新API Key信息
认证: Bearer Token

请求体:
{
  "name": "新名称",
  "rate_limit_rpm": 2000,
  "daily_quota": 200000
}

响应:
{
  "code": 0,
  "message": "更新成功",
  "data": {...}
}
```

#### 2.5.5 禁用/启用API Key

```yaml
// 禁用
接口: POST /api/v1/quota/keys/{key_id}/disable
说明: 禁用API Key
认证: Bearer Token

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "uuid",
    "status": "disabled"
  }
}

// 启用
接口: POST /api/v1/quota/keys/{key_id}/enable
说明: 启用API Key
认证: Bearer Token

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "uuid",
    "status": "active"
  }
}
```

#### 2.5.6 删除API Key

```yaml
接口: DELETE /api/v1/quota/keys/{key_id}
说明: 删除API Key
认证: Bearer Token

响应:
{
  "code": 0,
  "message": "删除成功",
  "data": null
}
```

#### 2.5.7 获取配额概览

```yaml
接口: GET /api/v1/quota/overview
说明: 获取所有API Key的配额概览
认证: Bearer Token

响应:
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "api_key_id": "uuid",
      "daily": {
        "used": 5000,
        "limit": 100000,
        "remaining": 95000
      },
      "monthly": {
        "used": 50000,
        "limit": null,
        "remaining": null
      }
    }
  ]
}
```

#### 2.5.8 获取配额使用历史

```yaml
接口: GET /api/v1/quota/usage-history/{key_id}
说明: 获取配额使用历史
认证: Bearer Token

查询参数:
  period_type: string, 周期类型 (daily/monthly)，默认daily
  days: int, 查询天数，默认14

响应:
{
  "code": 0,
  "message": "success",
  "data": [
    {"date": "2026-04-11", "total_amount": 10.5, "call_count": 105},
    {"date": "2026-04-12", "total_amount": 15.2, "call_count": 152},
    {"date": "2026-04-13", "total_amount": 8.3, "call_count": 83}
  ]
}
```

#### 2.5.9 获取调用日志

```yaml
接口: GET /api/v1/quota/logs
说明: 获取API调用日志
认证: Bearer Token

查询参数:
  page: int, 页码
  page_size: int, 每页数量
  key_id: string, API Key ID (可选)
  repo_id: string, 仓库ID (可选)
  start_date: string, 开始日期 (可选)
  end_date: string, 结束日期 (可选)

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "log_uuid",
        "request_id": "req_xxx",
        "api_key_id": "key_uuid",
        "api_key_name": "测试Key",
        "repo_id": "repo_xxx",
        "repo_name": "心理问答",
        "endpoint": "/chat",
        "method": "POST",
        "request_params": {...},
        "response_status": 200,
        "latency_ms": 150,
        "tokens_used": 100,
        "cost": 0.01,
        "ip_address": "1.2.3.4",
        "user_agent": "Mozilla/5.0...",
        "error_message": null,
        "created_at": "2026-04-17T10:00:00"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  }
}
```

### 2.6 账单管理API（控制台）

#### 2.6.1 获取账户信息

```yaml
接口: GET /api/v1/billing/account
说明: 获取当前用户的账户信息
认证: Bearer Token

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "account_uuid",
    "user_id": "user_uuid",
    "balance": 100.00,
    "currency": "CNY",
    "status": "active",
    "created_at": "2026-04-01T10:00:00",
    "updated_at": "2026-04-18T10:00:00"
  }
}
```

#### 2.6.2 账户充值

```yaml
接口: POST /api/v1/billing/recharge
说明: 账户充值
认证: Bearer Token

请求体:
{
  "amount": 100.00,
  "payment_method": "alipay",
  "remark": "充值备注"
}

响应:
{
  "code": 0,
  "message": "充值成功",
  "data": {
    "bill_no": "BILL202604180001",
    "amount": 100.00,
    "balance_before": 0.00,
    "balance_after": 100.00,
    "payment_status": "pending",
    "created_at": "2026-04-18T10:00:00"
  }
}
```

#### 2.6.3 获取账单列表

```yaml
接口: GET /api/v1/billing/bills
说明: 获取账单列表
认证: Bearer Token

查询参数:
  page: int, 页码，默认1
  page_size: int, 每页数量，默认20
  bill_type: string, 账单类型 (recharge/consumption)，可选
  start_date: string, 开始日期，可选
  end_date: string, 结束日期，可选

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "bill_uuid",
        "bill_no": "BILL202604180001",
        "account_id": "account_uuid",
        "bill_type": "recharge",
        "amount": 100.00,
        "balance_before": 0.00,
        "balance_after": 100.00,
        "payment_method": "alipay",
        "payment_status": "completed",
        "transaction_no": "ALIPAY20260418001",
        "remark": "充值备注",
        "created_at": "2026-04-18T10:00:00"
      },
      {
        "id": "bill_uuid2",
        "bill_no": "BILL202604170002",
        "account_id": "account_uuid",
        "bill_type": "consumption",
        "amount": -10.50,
        "balance_before": 110.50,
        "balance_after": 100.00,
        "payment_method": null,
        "payment_status": "completed",
        "transaction_no": null,
        "remark": "API调用消费",
        "created_at": "2026-04-17T23:59:59"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 50,
      "total_pages": 3
    }
  }
}
```

#### 2.6.4 获取消费趋势

```yaml
接口: GET /api/v1/billing/consumption-trend
说明: 获取消费趋势
认证: Bearer Token

查询参数:
  days: int, 查询天数，默认7

响应:
{
  "code": 0,
  "message": "success",
  "data": [
    {"date": "2026-04-11", "total_amount": 50.00, "call_count": 500},
    {"date": "2026-04-12", "total_amount": 75.00, "call_count": 750},
    {"date": "2026-04-13", "total_amount": 45.00, "call_count": 450},
    {"date": "2026-04-14", "total_amount": 80.00, "call_count": 800},
    {"date": "2026-04-15", "total_amount": 60.00, "call_count": 600},
    {"date": "2026-04-16", "total_amount": 55.00, "call_count": 550},
    {"date": "2026-04-17", "total_amount": 70.00, "call_count": 700}
  ]
}
```

---

## 3. 管理API（控制台）

### 3.1 认证接口

#### 3.1.1 用户登录

```yaml
接口: POST /api/v1/auth/login
说明: 用户登录，获取访问令牌（支持用户名或邮箱）

请求体（二选一）:
{
  "username": "admin",              # 用户名登录（可选）
  "email": "user@example.com",     # 邮箱登录（可选，与 username 二选一）
  "password": "your_password"
}

响应:
{
  "code": 0,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}

错误响应 - 用户名/邮箱或密码错误:
{
  "code": 40101,
  "message": "用户名/邮箱或密码错误",
  "data": null
}
```

#### 认证错误响应说明

| 场景 | 错误码 | 消息 | 前端显示标题 |
|------|--------|------|-------------|
| 用户名/邮箱或密码错误 | 40101 | "用户名/邮箱或密码错误" | 登录失败 |
| Token无效或已过期 | 40102 | "Token无效或已过期，请重新登录" | 登录已过期 |
| API Key已禁用 | 40103 | "API Key已禁用" | API Key已禁用 |
| API Key已过期 | 40104 | "API Key已过期" | API Key已过期 |
| API Key无效 | 40105 | "API Key无效" | API Key无效 |

**注意**: 前端应根据 `code` 值判断具体错误类型并显示相应的标题和消息。

#### 3.1.2 获取当前用户信息

```yaml
接口: GET /api/v1/auth/me
说明: 获取当前登录用户信息（包含 username, role, permissions）

请求头:
  Authorization: Bearer <access_token>

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "user_xxx",
    "username": "admin",
    "email": "user@example.com",
    "user_type": "admin",
    "user_status": "active",
    "role": "admin",
    "permissions": ["*"],
    "phone": "13800138000",
    "vip_level": 3,
    "email_verified": true,
    "created_at": "2026-04-16T10:00:00Z",
    "last_login_at": "2026-04-18T01:00:00Z"
  }
}

错误响应 - Token无效或已过期:
{
  "code": 40102,
  "message": "Token无效或已过期，请重新登录",
  "data": null
}
```

#### 3.1.3 用户登出

```yaml
接口: POST /api/v1/auth/logout
说明: 用户登出，使令牌失效

请求头:
  Authorization: Bearer <access_token>

响应:
{
  "code": 0,
  "message": "登出成功",
  "data": {
    "message": "登出成功"
  }
}
```

#### 3.1.4 Token刷新

```yaml
接口: POST /api/v1/auth/refresh
说明: 刷新JWT访问令牌

请求头:
  Authorization: Bearer <refresh_token>

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 86400
  }
}
```

### 3.2 用户管理

#### 3.2.1 用户注册

```yaml
接口: POST /api/v1/auth/register
说明: 注册新用户（支持 username 和 role）

请求体:
{
  "username": "newuser",           # 用户名（可选，唯一）
  "email": "user@example.com",     # 邮箱（必填，唯一）
  "password": "xxxx",              # 密码（至少8位）
  "user_type": "developer",       # 用户类型
  "role": "developer",            # 角色：user/developer/admin/super_admin
  "nickname": "张三"               # 昵称（可选）
}

响应:
{
  "code": 0,
  "message": "注册成功",
  "data": {
    "id": "user_xxx",
    "username": "newuser",
    "email": "user@example.com",
    "user_type": "developer",
    "role": "developer",
    "created_at": "2026-04-18T15:00:00Z"
  }
}
```
  "data": {
    "id": "user_xxx",
    "email": "user@example.com",
    "user_type": "developer",
    "status": "active",
    "created_at": "2026-04-16T10:00:00Z"
  }
}
```

#### 3.1.2 用户列表

```yaml
接口: GET /v1/admin/users
说明: 获取用户列表

查询参数:
  user_type: string, 用户类型
  status: string, 状态
  keyword: string, 关键词搜索
  page: int, 页码
  page_size: int, 每页数量

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [...],
    "pagination": {...}
  }
}
```

### 3.2 API Key管理

#### 3.2.1 创建Key

```yaml
接口: POST /v1/admin/keys
说明: 为用户创建API Key（管理后台）

请求体:
{
  "user_id": "user_xxx",
  "name": "生产环境Key",
  "allowed_repos": ["repo_xxx"],
  "rate_limit_rpm": 1000,
  "daily_quota": 100000
}

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "key_xxx",
    "key": "sk_live_xxxxxxxx",
    "secret": "xxxxxxxx",
    "name": "生产环境Key",
    "status": "active",
    "created_at": "2026-04-16T10:00:00Z"
  }
}
```

#### 3.2.2 Key列表

```yaml
接口: GET /v1/admin/keys
说明: 获取所有Key列表

查询参数:
  user_id: string, 用户ID
  status: string, 状态
  page: int, 页码
  page_size: int, 每页数量
```

### 3.3 仓库管理

#### 3.3.1 仓库注册

```yaml
接口: POST /v1/repositories
说明: 仓库所有者注册新仓库
认证: Bearer Token (owner/super_admin)

请求体:
{
  "name": "my-repo",
  "display_name": "我的仓库",
  "description": "仓库描述",
  "repo_type": "psychology",  # psychology/stock/ai/translation/vision/custom
  "protocol": "http",          # http/grpc/websocket
  "endpoint_url": "https://api.example.com",
  "config": {
    "timeout": 30000,
    "retry": 3
  }
}

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "uuid",
    "name": "my-repo",
    "slug": "my-repo",
    "status": "pending",       # 初始状态为待审核
    "created_at": "2026-04-19T22:00:00Z"
  }
}
```

#### 3.3.2 获取所有仓库（管理员）

```yaml
接口: GET /v1/repositories/admin/all
说明: 管理员获取所有仓库
认证: Bearer Token (admin/super_admin)

查询参数:
- status: 状态筛选 (pending/approved/rejected/online/offline)
- page: 页码 (默认1)
- page_size: 每页数量 (默认20)

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "uuid",
        "name": "repo-name",
        "slug": "repo-name",
        "display_name": "仓库显示名",
        "status": "pending",
        "owner": {
          "id": "user-uuid",
          "name": "owner_name"
        },
        "created_at": "2026-04-19T22:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 5,
      "total_pages": 1
    }
  }
}
```

#### 3.3.3 仓库审核（审核通过）

```yaml
接口: POST /v1/repositories/{repo_id}/approve
说明: 审核通过仓库
认证: Bearer Token (admin/super_admin)

请求体:
{
  "comment": "审核通过，备注信息（可选）"
}

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "uuid",
    "name": "repo-name",
    "status": "approved",
    "approved_at": "2026-04-19T22:30:00Z"
  }
}
```

#### 3.3.4 仓库审核（审核拒绝）

```yaml
接口: POST /v1/repositories/{repo_id}/reject
说明: 审核拒绝仓库
认证: Bearer Token (admin/super_admin)

请求体:
{
  "reason": "拒绝原因（可选）"
}

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "uuid",
    "name": "repo-name",
    "status": "rejected"
  }
}
```

#### 3.3.5 仓库上线

```yaml
接口: POST /v1/repositories/{repo_id}/online
说明: 上线仓库（需要先审核通过）
认证: Bearer Token (admin/super_admin)

前置条件: 仓库状态必须为 approved 或 offline

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "uuid",
    "name": "repo-name",
    "status": "online",
    "online_at": "2026-04-19T22:30:00Z"
  }
}
```

#### 3.3.6 仓库下线

```yaml
接口: POST /v1/repositories/{repo_id}/offline
说明: 下线仓库
认证: Bearer Token (admin/super_admin)

前置条件: 仓库状态必须为 online

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "uuid",
    "name": "repo-name",
    "status": "offline",
    "offline_at": "2026-04-19T22:30:00Z"
  }
}
```

### 3.5 超级管理员用户管理 (V1.6新增)

超级管理员用户管理接口提供用户的查询、更新、禁用和删除功能。**重要**：只有 `super_admin` 角色的用户可以访问这些接口。

#### 3.5.1 获取用户列表

```yaml
接口: GET /v1/superadmin/users
说明: 获取用户列表
认证: Bearer Token (super_admin)

查询参数:
- page: 页码 (默认1)
- page_size: 每页数量 (默认10)
- keyword: 搜索关键词（用户名/邮箱）
- user_type: 用户类型筛选 (super_admin/admin/owner/developer/user)
- user_status: 用户状态筛选 (active/inactive/suspended/deleted)

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "uuid",
        "username": "admin",
        "email": "admin@example.com",
        "phone": "13800000000",
        "user_type": "admin",
        "role": "admin",
        "user_status": "active",
        "vip_level": 3,
        "permissions": ["*"],
        "created_at": "2026-04-19T13:41:48",
        "last_login_at": "2026-04-19T13:41:48"
      }
    ],
    "total": 5,
    "page": 1,
    "page_size": 10
  }
}
```

#### 3.5.2 更新用户信息

```yaml
接口: PUT /v1/superadmin/users/{user_id}
说明: 更新用户信息
认证: Bearer Token (super_admin)

请求参数 (Query):
- user_type: 用户类型 (可选)
- role: 角色 (可选)
- user_status: 用户状态 (可选: active/suspended)
- vip_level: VIP等级 (可选)

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "uuid",
    "username": "admin",
    "user_status": "suspended"
  }
}
```

#### 3.5.3 删除用户

```yaml
接口: DELETE /v1/superadmin/users/{user_id}
说明: 删除用户（软删除）
认证: Bearer Token (super_admin)

响应:
{
  "code": 0,
  "message": "用户已删除",
  "data": null
}
```

**业务规则**：
- 超级管理员 (`super_admin`) 不能被删除
- 删除为软删除，将用户状态设置为 `deleted`

#### 3.5.4 用户状态说明

| 状态 | 说明 |
|------|------|
| active | 正常，可登录 |
| inactive | 未激活（注册后未验证） |
| suspended | 已禁用，无法登录 |
| deleted | 已删除（软删除） |

#### 3.5.5 测试账号

| 角色 | 邮箱 | 密码 | 说明 |
|------|------|------|------|
| 超级管理员 | superadmin@example.com | super123456 | 拥有所有权限 |
| 管理员 | admin@example.com | admin123 | 无法访问用户管理接口 |

### 3.6 管理员用户管理 (V1.7新增)

管理员用户管理接口提供对普通用户的查询、更新、禁用和删除功能。只有 `admin` 或 `super_admin` 角色的用户可以访问这些接口。管理员只能管理非管理员用户。

#### 3.6.1 获取用户列表

```yaml
接口: GET /v1/admin/users
认证: Bearer Token (admin/super_admin)
说明: 管理员获取用户列表（不包括超级管理员）

查询参数:
- page: 页码 (默认1)
- page_size: 每页数量 (默认10)
- keyword: 搜索关键词（用户名/邮箱）
- user_type: 用户类型筛选 (owner/developer/user)
- user_status: 用户状态筛选

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [...],
    "total": 4,
    "page": 1,
    "page_size": 10
  }
}
```

#### 3.6.2 更新用户信息

```yaml
接口: PUT /v1/admin/users/{user_id}
认证: Bearer Token (admin/super_admin)
说明: 管理员更新用户状态和VIP等级

请求体 (JSON):
{
  "user_status": "suspended",  # 用户状态 (可选)
  "vip_level": 1               # VIP等级 (可选)
}

响应 200:
{
  "code": 0,
  "message": "success",
  "data": {...}
}

响应 403:
{
  "code": 403,
  "message": "无权修改管理员或超级管理员的账户"
}
```

#### 3.6.3 删除用户

```yaml
接口: DELETE /v1/admin/users/{user_id}
认证: Bearer Token (admin/super_admin)
说明: 管理员删除用户

响应 200:
{
  "code": 0,
  "message": "用户已删除",
  "data": {"id": "uuid"}
}

响应 403:
{
  "code": 403,
  "message": "无权删除管理员或超级管理员账户"
}
```

#### 3.6.4 权限说明

| 用户类型 | 权限 | 可执行操作 |
|----------|------|-----------|
| super_admin | 所有权限 | 查询、更新、禁用、删除所有用户 |
| admin | user:manage | 查询、更新、禁用、删除普通用户 |
| 其他 | 受限 | 无权访问 |

#### 3.6.5 管理员 vs 超级管理员

| 功能 | 超级管理员 | 管理员 |
|------|-----------|--------|
| 查看所有用户 | ✅ | ❌ 不显示超级管理员 |
| 修改用户类型/角色 | ✅ | ❌ |
| 修改用户权限 | ✅ | ❌ |
| 修改用户状态 | ✅ | ✅ 只能普通用户 |
| 修改VIP等级 | ✅ | ✅ 只能普通用户 |
| 删除用户 | ✅ | ❌ 不能删除管理员 |

### 3.4 适配器管理

#### 3.4.1 适配器列表

```yaml
接口: GET /v1/admin/adapters
说明: 获取适配器列表

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "adapter_http",
        "name": "HTTP适配器",
        "adapter_type": "http",
        "version": "1.0.0",
        "status": "active",
        "total_repos": 20
      },
      {
        "id": "adapter_grpc",
        "name": "gRPC适配器",
        "adapter_type": "grpc",
        "version": "1.0.0",
        "status": "active",
        "total_repos": 5
      }
    ]
  }
}
```

#### 3.4.2 创建适配器

```yaml
接口: POST /v1/admin/adapters
说明: 创建新适配器

请求体:
{
  "name": "自定义适配器",
  "adapter_type": "http",
  "version": "1.0.0",
  "config_schema": {
    "type": "object",
    "properties": {
      "base_url": {"type": "string"},
      "timeout": {"type": "number"}
    }
  },
  "capabilities": {
    "auth": ["api_key", "bearer"],
    "transform": true
  }
}
```

### 3.5 账单管理

#### 3.5.1 账单列表

```yaml
接口: GET /v1/admin/bills
说明: 获取账单列表

查询参数:
  user_id: string, 用户ID
  bill_type: string, 账单类型
  start_time: timestamp, 开始时间
  end_time: timestamp, 结束时间
  page: int, 页码
  page_size: int, 每页数量
```

#### 3.5.2 用户充值

```yaml
接口: POST /v1/admin/accounts/recharge
说明: 管理员为用户充值

请求体:
{
  "user_id": "user_xxx",
  "amount": 100.00,
  "payment_method": "admin",
  "remark": "管理员赠送"
}

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "bill_no": "BILL202604160001",
    "amount": 100.00,
    "balance_after": 200.00
  }
}
```

### 3.6 统计数据

#### 3.6.1 平台概览

```yaml
接口: GET /v1/admin/stats/overview
说明: 获取平台统计概览

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "users": {
      "total": 10000,
      "developers": 9000,
      "owners": 1000
    },
    "repositories": {
      "total": 50,
      "internal": 10,
      "external": 40,
      "online": 45
    },
    "calls": {
      "today": 1000000,
      "this_month": 30000000
    },
    "revenue": {
      "today": 10000.00,
      "this_month": 300000.00
    }
  }
}
```

---

## 4. Webhook接口

### 4.1 仓库回调

```yaml
接口: POST /v1/webhooks/repository
说明: 接收仓库事件回调

请求头:
  X-Webhook-Signature: <hmac_signature>
  X-Webhook-Timestamp: <timestamp>
  Content-Type: application/json

请求体:
{
  "event": "call_completed",
  "repo_id": "repo_xxx",
  "data": {
    "request_id": "req_xxx",
    "status": "success",
    "latency_ms": 150
  },
  "timestamp": 1640000000000
}

验证签名:
  signature = HMAC-SHA256(secret, timestamp + body)
```

### 4.2 事件类型

| 事件 | 说明 | 触发时机 |
|------|------|----------|
| call_completed | 调用完成 | 每次API调用完成 |
| repo_online | 仓库上线 | 仓库从下线变为上线 |
| repo_offline | 仓库下线 | 仓库从上线变为下线 |
| quota_alert | 配额告警 | 配额使用达到阈值 |
| payment_success | 充值成功 | 用户充值完成 |

---

## 5. 内部API

### 5.1 服务认证

```yaml
请求头:
  X-Service-Token: <service_token>
  X-Service-Name: <service_name>
```

### 5.2 服务间调用

```yaml
接口: POST /v1/internal/usage/report
说明: 上报调用用量（计费服务调用）

请求体:
{
  "key_id": "key_xxx",
  "repo_id": "repo_xxx",
  "request_id": "req_xxx",
  "tokens_used": 100,
  "cost": 0.01,
  "latency_ms": 150,
  "timestamp": 1640000000000
}
```

---

## 6. 附录

### 6.1 HTTP状态码

| 状态码 | 说明 |
|--------|------|
| 200 | OK |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Too Many Requests |
| 500 | Internal Server Error |
| 502 | Bad Gateway |
| 503 | Service Unavailable |

### 6.2 通用响应格式

```yaml
成功:
{
  "code": 0,
  "message": "success",
  "data": {...}
}

失败:
{
  "code": 40001,
  "message": "错误描述",
  "request_id": "req_xxx",
  "details": {...}
}
```

### 6.3 分页响应格式

```yaml
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  }
}
```
