# 通用API服务平台 - 接口设计文档

## 文档信息

| 属性 | 内容 |
|------|------|
| **文档编号** | API-PLATFORM-2026-001 |
| **版本** | V1.0 |
| **日期** | 2026-04-16 |

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
| 40101 | UNAUTHORIZED | 未认证 |
| 40102 | INVALID_KEY | API Key无效 |
| 40103 | KEY_DISABLED | Key已禁用 |
| 40104 | KEY_EXPIRED | Key已过期 |
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

### 2.5 配额查询API

#### 2.5.1 配额信息

```yaml
接口: GET /v1/quota
说明: 查询当前配额使用情况

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "rpm": {
      "limit": 1000,
      "used": 150,
      "remaining": 850,
      "reset_at": 1640000000
    },
    "rph": {
      "limit": 10000,
      "used": 5000,
      "remaining": 5000,
      "reset_at": 1640080000
    },
    "daily": {
      "limit": 100000,
      "used": 50000,
      "remaining": 50000,
      "reset_at": 1640124800
    },
    "balance": {
      "amount": 100.00,
      "currency": "CNY"
    }
  }
}
```

---

## 3. 管理API（控制台）

### 3.1 用户管理

#### 3.1.1 用户注册

```yaml
接口: POST /v1/admin/users
说明: 创建用户（管理后台）

请求头:
  Authorization: Bearer <admin_token>

请求体:
{
  "email": "user@example.com",
  "password": "xxxx",
  "user_type": "developer",
  "nickname": "张三"
}

响应:
{
  "code": 0,
  "message": "success",
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
接口: POST /v1/admin/repositories
说明: 注册新仓库

请求体:
{
  "owner_id": "user_xxx",
  "owner_type": "internal",
  "name": "psychology",
  "display_name": "心理问答",
  "description": "专业心理问答服务",
  "repo_type": "psychology",
  "protocol": "http",
  "endpoint_url": "https://internal-service/psychology",
  "config": {
    "timeout": 30000,
    "retry": 3
  },
  "pricing": {
    "type": "token",
    "price_per_token": 0.001
  }
}

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "repo_xxx",
    "status": "pending",
    "created_at": "2026-04-16T10:00:00Z"
  }
}
```

#### 3.3.2 仓库审核

```yaml
接口: POST /v1/admin/repositories/{repo_id}/approve
说明: 审核通过仓库

请求体:
{
  "comment": "审核通过"
}

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "repo_xxx",
    "status": "approved",
    "approved_at": "2026-04-16T10:00:00Z"
  }
}
```

#### 3.3.3 仓库上线

```yaml
接口: POST /v1/admin/repositories/{repo_id}/online
说明: 上线仓库

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "repo_xxx",
    "status": "online",
    "online_at": "2026-04-16T10:00:00Z"
  }
}
```

#### 3.3.4 仓库下线

```yaml
接口: POST /v1/admin/repositories/{repo_id}/offline
说明: 下线仓库

请求体:
{
  "reason": "服务升级"
}

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "repo_xxx",
    "status": "offline",
    "offline_at": "2026-04-16T10:00:00Z"
  }
}
```

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
