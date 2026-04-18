# 通用API服务平台 - FAQ 问题详解

## 文档控制

| 项目 | 内容 |
|------|------|
| 文档编号 | FAQ-API-2026-002 |
| 版本号 | V1.7 |
| 创建日期 | 2026-04-18 |
| 更新日期 | 2026-04-19 |
| 关联文档 | [13_FAQ常见问题.md](../Doc/13_FAQ常见问题.md) |

---

## FAQ 汇总列表

> 新增 FAQ 时，请在此处添加条目并同步更新

| 序号 | 问题标题 | 关键词 | 优先级 | 状态 |
|:----:|----------|--------|:------:|:----:|
| 33 | 登录失败时提示"登录已过期"，但明明是第一次登录 | 登录、过期、错误提示 | P0 | ✅ 已解决 |
| 34 | 接口文档错误码定义更新说明 | 错误码、40101、40102 | P1 | ✅ 已完成 |
| 35 | 添加 username 和 role 字段，支持用户名登录和权限管理 | username、role、权限 | P0 | ✅ 已完成 |
| 36 | 前端API调用返回数据缺少access_token - 统一响应格式问题 | 前端、响应格式、data字段 | P0 | ✅ 已解决 |
| 37 | 添加查看 API Key 明文功能 | API Key、查看、明文 | P1 | ✅ 已完成 |
| 38 | 配额使用情况页面报错：AttributeError: '_isnull' | 配额、SQLAlchemy、Bug | P0 | ✅ 已修复 |
| 39 | 账单中心报错：function sum(character varying) does not exist | 账单、PostgreSQL、Bug | P0 | ✅ 已修复 |

**优先级说明**：P0=紧急/影响核心功能，P1=重要/影响常用功能，P2=一般/影响体验

**更新说明**：添加新 FAQ 时，请在列表中添加对应条目，并在文档末尾更新版本和变更记录。

---

## 问题33：登录失败时提示"登录已过期"，但明明是第一次登录

### 33.1 问题描述

用户在登录页面输入用户名和密码后，点击登录按钮，系统显示以下错误：

```
标题：登录已过期
副标题：请重新登录后继续操作
详细信息（开发模式）：
时间: 2026-04-18T14:41:01.688Z
```

但用户明确表示这是**第一次登录**，还没有进行过任何操作，"登录已过期"的提示明显不合理。

---

### 33.2 问题分析

#### 33.2.1 错误来源追踪

通过浏览器开发者工具（F12 → Network 标签）查看网络请求：

1. **登录请求** (`POST /api/v1/auth/login`)
   - 请求体：`{"email":"admin","password":"admin123"}`
   - 响应状态码：401
   - 响应体：`{"code":40101,"message":"用户名/邮箱或密码错误","data":null}`

2. **用户信息请求** (`GET /api/v1/auth/me`)
   - 由于没有获取到 Token，请求未正确发送或返回错误

#### 33.2.2 问题根源

经过排查，发现**两个问题**：

**问题一：后端认证错误类型未区分**

后端使用单一的 `AuthenticationError` 处理所有认证失败场景：
- 用户名/邮箱或密码错误 → 返回 "用户名/邮箱或密码错误"
- Token 无效/过期 → 也返回相同的错误消息

前端根据 HTTP 状态码 401 显示固定标题 "登录已过期"，导致用户困惑。

**问题二：测试账号错误**

数据库中的测试账号邮箱是：
| 角色 | 邮箱 | 密码 |
|------|------|------|
| 管理员 | admin@example.com | admin123 |
| 开发者 | developer@example.com | admin123 |
| 仓库所有者 | owner@example.com | admin123 |

用户输入的是 `admin`（用户名），而系统要求的是邮箱格式 `admin@example.com`。

---

### 33.3 解决方案

#### 33.3.1 后端改进：区分认证错误类型

**问题一：后端认证错误类型未区分**

后端使用单一的 `AuthenticationError` 处理所有认证失败场景，导致前端无法区分"用户名密码错误"和"Token过期"。

**解决方案**：新增专门的异常类型

**新增异常类型** (`src/core/exceptions.py`)：

```python
class TokenExpiredError(AuthenticationError):
    """Token has expired - Token已过期"""

    def __init__(self, message: str = "Token has expired, please login again"):
        super().__init__(message, code=40102)


class InvalidCredentialsError(AuthenticationError):
    """Invalid username or password - 用户名或密码错误"""

    def __init__(self, message: str = "Invalid username/email or password"):
        super().__init__(message, code=40101)
```

**修改 Token 验证逻辑** (`src/core/security.py`)：

```python
def verify_token(token: str) -> dict:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        # JWT 解码失败，可能是 Token 无效或已过期
        raise TokenExpiredError("Token无效或已过期，请重新登录")
```

**修改认证服务** (`src/services/auth_service.py`)：

```python
async def get_current_user(credentials: HTTPAuthorizationCredentials, db: AsyncSession):
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise TokenExpiredError("Token无效，请重新登录")
    
    user_id = payload.get("sub")
    if not user_id:
        raise TokenExpiredError("Token无效，请重新登录")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise TokenExpiredError("用户不存在，请重新登录")
```

#### 33.3.2 前端改进：错误消息显示和动态标题

**问题二：前端标题固定显示"登录已过期"**

后端虽然返回了正确的错误码和消息，但前端弹窗的标题是固定的，无法区分不同场景。

**解决方案**：根据错误码动态显示标题和副标题

```tsx
// 认证错误码对应的标题和副标题
const authErrorConfigByCode: Record<number, { title: string; subTitle: string }> = {
  40101: { title: '登录失败', subTitle: '用户名/邮箱或密码错误，请检查后重试' },
  40102: { title: '登录已过期', subTitle: '请重新登录后继续操作' },
  40103: { title: 'API Key已禁用', subTitle: '请联系管理员启用您的API Key' },
  40104: { title: 'API Key已过期', subTitle: '请联系管理员续期您的API Key' },
  40105: { title: 'API Key无效', subTitle: '请检查您的API Key是否正确' },
}

// 获取认证错误的配置（根据错误码）
function getAuthErrorConfig(error: any): ErrorConfig {
  const code = error?.response?.data?.code || error?.code
  const customConfig = authErrorConfigByCode[code]
  
  if (customConfig) {
    return {
      icon: <LogoutOutlined style={{ color: '#faad14', fontSize: 48 }} />,
      title: customConfig.title,
      subTitle: customConfig.subTitle,
      showLogout: true,
    }
  }
  
  // 默认配置
  return {
    icon: <LogoutOutlined style={{ color: '#faad14', fontSize: 48 }} />,
    title: '登录已过期',
    subTitle: '请重新登录后继续操作',
    showLogout: true,
  }
}
```

**同时使用 Alert 组件显示具体错误消息**：

```tsx
<Alert 
  message={errorMessage}
  type={errorType === ErrorType.AUTH ? "warning" : "error"}
  showIcon
  style={{ maxWidth: 400, margin: '0 auto' }}
/>
```

---

### 33.4 错误码对照表（前端显示）

修改后，系统的前端弹窗标题会根据错误码动态显示：

| 错误码 | 弹窗标题 | 副标题 | 后端返回消息 |
|--------|---------|--------|-------------|
| 40101 | **登录失败** | 用户名/邮箱或密码错误，请检查后重试 | "用户名/邮箱或密码错误" |
| 40102 | **登录已过期** | 请重新登录后继续操作 | "Token无效或已过期，请重新登录" |
| 40103 | **API Key已禁用** | 请联系管理员启用您的API Key | "API Key已禁用" |
| 40104 | **API Key已过期** | 请联系管理员续期您的API Key | "API Key已过期" |
| 40105 | **API Key无效** | 请检查您的API Key是否正确 | "API Key无效" |

---

---

### 33.5 正确的测试账号

**支持两种登录方式**：用户名登录 或 邮箱登录

| 用户类型 | username | email | 密码 | role | VIP等级 |
|----------|----------|-------|------|------|---------|
| 管理员 | admin | admin@example.com | admin123 | admin | 3 |
| 开发者 | developer | developer@example.com | dev123456 | user | 1 |
| 仓库所有者 | owner | owner@example.com | owner123 | developer | 2 |
| 测试用户 | test | test@example.com | test123 | user | 0 |

**登录示例**：

```json
// 方式1：使用用户名登录
{"username": "admin", "password": "admin123"}

// 方式2：使用邮箱登录
{"email": "admin@example.com", "password": "admin123"}
```

**角色说明**：
- `admin`: 管理员，拥有所有权限 (`*`)
- `developer`: 开发者，拥有 API 读写权限
- `user`: 普通用户，仅有只读权限

---

### 33.6 验证修复

修复后，使用正确的账号登录：

```bash
# 测试登录
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'

# 响应
{
  "code": 0,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```

使用错误的密码登录：

```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"wrongpassword"}'

# 响应 - 现在显示正确的错误消息
{
  "code": 40101,
  "message": "用户名/邮箱或密码错误",
  "data": null
}
```

使用无效的 Token 访问受保护接口：

```bash
curl -X GET http://localhost:8080/api/v1/auth/me \
  -H "Authorization: Bearer invalid_token"

# 响应 - 现在显示正确的错误消息
{
  "code": 40102,
  "message": "Token无效或已过期，请重新登录",
  "data": null
}
```

---

## 问题34：接口文档错误码定义更新说明

### 34.1 背景

为解决问题33中对认证错误类型的区分，对接口设计文档中的错误码定义进行了更新。

### 34.2 更新内容

#### 34.2.1 错误码名称和说明更新

| 错误码 | 原名称 | 新名称 | 原说明 | 新说明 |
|--------|--------|--------|--------|--------|
| 40101 | UNAUTHORIZED | INVALID_CREDENTIALS | 未认证 | 用户名/邮箱或密码错误 |
| 40102 | INVALID_KEY | TOKEN_EXPIRED | API Key无效 | Token无效或已过期 |

#### 34.2.2 新增错误码

| 错误码 | 名称 | 说明 |
|--------|------|------|
| 40105 | INVALID_KEY | API Key无效 |

### 34.3 前端错误显示逻辑

前端根据后端返回的错误码动态显示不同的标题和消息：

```typescript
// 认证错误码与前端显示的对应关系
const authErrorConfigByCode: Record<number, { title: string; subTitle: string }> = {
  40101: { title: '登录失败', subTitle: '用户名/邮箱或密码错误，请检查后重试' },
  40102: { title: '登录已过期', subTitle: '请重新登录后继续操作' },
  40103: { title: 'API Key已禁用', subTitle: '请联系管理员启用您的API Key' },
  40104: { title: 'API Key已过期', subTitle: '请联系管理员续期您的API Key' },
  40105: { title: 'API Key无效', subTitle: '请检查您的API Key是否正确' },
}
```

### 34.4 认证接口错误响应示例

#### 登录接口 (`POST /api/v1/auth/login`)

**成功响应**：
```json
{
  "code": 0,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```

**错误响应 - 用户名/邮箱或密码错误**：
```json
{
  "code": 40101,
  "message": "用户名/邮箱或密码错误",
  "data": null
}
```

#### 获取用户信息接口 (`GET /api/v1/auth/me`)

**成功响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "user_xxx",
    "email": "user@example.com",
    "user_type": "admin",
    "user_status": "active",
    "created_at": "2026-04-16T10:00:00Z"
  }
}
```

**错误响应 - Token无效或已过期**：
```json
{
  "code": 40102,
  "message": "Token无效或已过期，请重新登录",
  "data": null
}
```

### 34.5 前端开发建议（已实现）

项目中已使用 `ErrorContext` 统一处理错误，错误码对应的标题和消息在 `authErrorConfigByCode` 中配置：

```typescript
// 位置：web/src/contexts/ErrorContext.tsx

// 认证错误码对应的标题和副标题
const authErrorConfigByCode: Record<number, { title: string; subTitle: string }> = {
  40101: { title: '登录失败', subTitle: '用户名/邮箱或密码错误，请检查后重试' },
  40102: { title: '登录已过期', subTitle: '请重新登录后继续操作' },
  40103: { title: 'API Key已禁用', subTitle: '请联系管理员启用您的API Key' },
  40104: { title: 'API Key已过期', subTitle: '请联系管理员续期您的API Key' },
  40105: { title: 'API Key无效', subTitle: '请检查您的API Key是否正确' },
}

// 获取认证错误的配置（根据错误码）
function getAuthErrorConfig(error: any): ErrorConfig {
  const code = error?.response?.data?.code || error?.code
  const customConfig = authErrorConfigByCode[code]
  
  if (customConfig) {
    return {
      icon: <LogoutOutlined style={{ color: '#faad14', fontSize: 48 }} />,
      title: customConfig.title,
      subTitle: customConfig.subTitle,
      showLogout: true,
    }
  }
  // ...
}
```

**使用方式**：

```tsx
import { useError } from '../contexts/ErrorContext'

const MyComponent = () => {
  const { showError } = useError()
  
  const handleLogin = async () => {
    try {
      await login(email, password)
    } catch (error) {
      // 错误会自动根据错误码显示正确的标题和消息
      showError(error)
    }
  }
}
```

---

## 附录：排查工具和命令

### A.1 查看后端日志

```powershell
# Windows PowerShell
# 查看认证相关日志
type "d:\Work_Area\AI\API-Agent\api-platform\logs\modules\middleware.log" | findstr "login me auth"

# 或实时查看日志
Get-Content "d:\Work_Area\AI\API-Agent\api-platform\logs\modules\middleware.log" -Wait
```

### A.2 检查端口占用

```powershell
# 检查后端服务是否运行
netstat -ano | findstr "8080"

# 检查 PostgreSQL
netstat -ano | findstr "5432"

# 检查 Redis
netstat -ano | findstr "6379"
```

### A.3 使用 curl 测试 API

```bash
# 测试登录接口
curl -X POST http://localhost:8080/api/v1/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"admin@example.com\",\"password\":\"admin123\"}"

# 测试用户信息接口（需要先登录获取 Token）
curl -X GET http://localhost:8080/api/v1/auth/me ^
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### A.4 数据库查询

```python
# 查询所有用户
cd d:\Work_Area\AI\API-Agent\api-platform
python -c "
import asyncio
from sqlalchemy import select
from src.config.database import AsyncSessionLocal
from src.models.user import User

async def check_users():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        for u in users:
            print(f'Email: {u.email}, Type: {u.user_type}, Status: {u.user_status}')

asyncio.run(check_users())
"
```

---

## 问题35：添加 username 和 role 字段，支持用户名登录和权限管理

### 35.1 背景

原系统设计存在以下问题：
1. 用户只能使用邮箱登录，不支持用户名登录
2. 权限控制粒度不够细致，只有 `user_type` 字段

### 35.2 解决方案

#### 35.2.1 数据库字段扩展

在 `users` 表中添加以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `username` | VARCHAR(50) | 用户名（唯一，可选） |
| `role` | VARCHAR(20) | 角色 |
| `permissions` | JSONB | 细粒度权限列表 |

#### 35.2.2 角色设计

| 角色 | 说明 | 默认权限 |
|------|------|---------|
| `super_admin` | 超级管理员 | `["*"]` (所有权限) |
| `admin` | 管理员 | 全部 API + 用户管理权限 |
| `developer` | 开发者 | API 读写权限 |
| `user` | 普通用户 | 只读权限 |

#### 35.2.3 权限列表设计

| 权限标识 | 说明 |
|----------|------|
| `*` | 所有权限（超级管理员） |
| `user:read` | 读取用户信息 |
| `user:write` | 创建/更新用户 |
| `user:delete` | 删除用户 |
| `api:read` | 读取 API 密钥 |
| `api:write` | 创建/更新 API 密钥 |
| `api:delete` | 删除 API 密钥 |
| `quota:manage` | 管理配额 |
| `repo:manage` | 管理仓库 |

### 35.3 代码修改

#### 35.3.1 User 模型 (`src/models/user.py`)

```python
class User(Base):
    __tablename__ = "users"
    
    # 登录凭证
    username = Column(String(50), unique=True, nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    
    # 用户类型和角色
    user_type = Column(String(20), nullable=False, default="developer")
    role = Column(String(20), nullable=False, default="user")
    permissions = Column(JSONB, default=list)
```

#### 35.3.2 登录接口 (`src/api/v1/auth.py`)

支持 username 或 email 登录：

```python
@router.post("/login")
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    # 通过 username 或 email 查找用户
    if "@" in login_value:
        # 邮箱登录
        result = await db.execute(
            select(User).where(User.email == login_value)
        )
    else:
        # 用户名登录
        result = await db.execute(
            select(User).where(User.username == login_value)
        )
```

#### 35.3.3 注册接口 (`src/api/v1/auth.py`)

创建用户时可指定 username 和 role：

```python
@router.post("/register")
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # 设置默认权限
    default_permissions = {
        "user": ["user:read"],
        "developer": ["user:read", "user:write", "api:read", "api:write"],
        "admin": ["user:read", "user:write", "user:delete", "api:*", "quota:manage"],
        "super_admin": ["*"]
    }
```

### 35.4 当前测试账号

| username | email | 密码 | user_type | role | 权限级别 |
|----------|-------|------|-----------|------|---------|
| `admin` | admin@example.com | admin123 | admin | admin | 管理员 |
| `developer` | developer@example.com | admin123 | developer | user | 普通用户 |
| `owner` | owner@example.com | admin123 | owner | developer | 开发者 |

### 35.5 API 变更

#### 登录接口 (`POST /api/v1/auth/login`)

**请求体**（二选一）：

```json
// 方式1：使用用户名登录
{
  "username": "admin",
  "password": "admin123"
}

// 方式2：使用邮箱登录
{
  "email": "admin@example.com",
  "password": "admin123"
}
```

**响应**（新增 role 和 permissions）：

```json
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
```

#### 获取用户信息接口 (`GET /api/v1/auth/me`)

**响应**（新增字段）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "user_xxx",
    "username": "admin",
    "email": "admin@example.com",
    "user_type": "admin",
    "role": "admin",
    "permissions": ["*"],
    "user_status": "active",
    "vip_level": 3,
    "created_at": "2026-04-16T10:00:00Z"
  }
}
```

#### 注册接口 (`POST /api/v1/auth/register`)

**请求体**（新增字段）：

```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "password123",
  "user_type": "developer",
  "role": "developer"
}
```

**响应**（新增字段）：

```json
{
  "code": 0,
  "message": "注册成功",
  "data": {
    "id": "user_xxx",
    "username": "newuser",
    "email": "newuser@example.com",
    "user_type": "developer",
    "role": "developer",
    "created_at": "2026-04-18T15:00:00Z"
  }
}
```

### 35.6 迁移脚本

```bash
# 数据库迁移脚本位置
cd d:\Work_Area\AI\API-Agent\api-platform
python migrations/add_user_fields.py
python migrations/update_user_data.py
```

---

## 问题36：前端API调用返回数据缺少access_token - 统一响应格式问题

### 36.1 问题描述

登录时提示"登录失败：未获取到访问令牌"，但后端日志显示登录成功并返回了 Token。

**前端日志**：
```
[Login] Failed {
  "message": "登录失败：未获取到访问令牌",
  "email": "admin"
}
```

**后端日志**（实际返回）：
```
{"code":0,"message":"success","data":{"access_token":"eyJ...","refresh_token":"eyJ...","expires_in":1800}}
```

---

### 36.2 问题分析

#### 36.2.1 响应格式差异

| 层级 | 返回格式 |
|------|---------|
| 后端实际返回 | `{ code: 0, message: "success", data: { access_token, ... } }` |
| 前端期望获取 | `{ access_token, refresh_token, expires_in }` |

#### 36.2.2 问题原因

前端 Axios 拦截器直接返回 `{ code, message, data }` 对象，但 API 调用代码期望直接获取 `data` 字段内容：

```typescript
// auth.ts
const response = await authApi.login({ email, password })
// response = { code: 0, message: "success", data: {...} }
// 代码期望: response.access_token，但实际是 response.data.access_token
```

---

### 36.3 解决方案

#### 36.3.1 修改 client.ts 响应拦截器（推荐）

在 `web/src/api/client.ts` 中修改响应拦截器，自动提取 `data` 字段：

```typescript
client.interceptors.response.use(
  (response) => {
    const { config, status, data } = response
    
    // 统一处理业务错误码
    if (data.code !== undefined && data.code !== 0) {
      const error = new Error(data.message || '请求失败')
      error.code = data.code
      return Promise.reject(error)
    }
    
    // 自动提取 data 字段（统一响应格式）
    // 后端返回: { code: 0, message: "success", data: {...} }
    // 前端直接获取: {...}
    const extractedData = data?.data !== undefined ? data.data : data
    
    return {
      ...response,
      data: extractedData,
    } as AxiosResponse
  },
  // ...
)
```

#### 36.3.2 修复后的使用方式

```typescript
// 修复后：直接获取业务数据
const tokenData = await authApi.login({ email, password })
// tokenData = { access_token, refresh_token, expires_in }
// 不需要 tokenData.data.access_token

const user = await authApi.me()
// user = { id, email, username, role, ... }
// 不需要 user.data.id
```

---

### 36.4 相关文件

| 文件 | 修改内容 |
|------|---------|
| `web/src/api/client.ts` | 响应拦截器自动提取 data 字段 |
| `web/src/api/auth.ts` | 保持简洁写法，利用 client.ts 自动处理 |

---

### 36.5 验证方法

1. **查看浏览器控制台 Network 标签**
   - 请求 `/api/v1/auth/login`
   - 响应 Preview 应显示：`{ code: 0, data: { access_token, ... } }`

2. **测试登录功能**
   - 清除浏览器缓存或使用隐私模式
   - 使用 `admin` / `admin123` 登录
   - 应成功跳转至管理后台

3. **API 调用测试**
   ```typescript
   // 浏览器控制台测试
   const res = await fetch('/api/v1/auth/login', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({ email: 'admin@example.com', password: 'admin123' })
   })
   const data = await res.json()
   console.log(data.data.access_token) // 正确获取 token
   ```

---

### 36.6 文档更新

此问题已更新至以下文档：

- `09_接口设计文档.md` - V2.2，新增 2.3.1 前端统一响应处理说明
- `13_FAQ常见问题.md` - V1.2，新增 Q36 统一响应格式问题
- `16_客户端技术方案.md` - V1.1，新增 4.4 统一响应格式处理章节

---

## 问题37：添加查看 API Key 明文功能

### 37.1 问题背景

用户创建 API Key 后，界面只显示 Key 前缀（如 `sk_bf58f809_****`），无法查看完整内容。用户担心丢失 key 后无法找回，希望能够随时查看完整的 API Key。

---

### 37.2 需求分析

**用户痛点**：
1. API Key 创建时只显示一次，如果用户没有保存就无法找回
2. 用户需要将 key 复制到其他应用使用
3. 管理员需要查看用户的所有 key

**安全考虑**：
1. API Key 不能以明文形式存储在数据库中
2. 查看 key 应该是受限操作，需要用户主动触发
3. 应该有适当的提示，提醒用户保护好 key

---

### 37.3 解决方案

#### 37.3.1 数据层设计

在 `api_keys` 表中添加 `encrypted_key` 字段，使用加密方式存储原始 key：

```python
# src/models/api_key.py
class APIKey(Base):
    # ... 其他字段 ...
    encrypted_key = Column(Text, nullable=True)  # 加密存储的原始 key
```

#### 37.3.2 加密实现

使用 `cryptography` 库的 Fernet 对称加密：

```python
# src/utils/crypto.py
from cryptography.fernet import Fernet

def encrypt_api_key(api_key: str) -> str:
    """加密 API key"""
    fernet = Fernet(get_encryption_key())
    return fernet.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """解密 API key"""
    fernet = Fernet(get_encryption_key())
    return fernet.decrypt(encrypted_key.encode()).decode()
```

#### 37.3.3 后端接口

添加查看 key 明文的接口：

```python
# src/api/v1/quota.py
@router.get("/keys/{key_id}/reveal")
async def reveal_key(key_id: str, current_user: User = Depends(get_current_user)):
    """
    查看 API Key 明文
    警告：此操作会暴露敏感信息，仅在必要时调用
    """
    # ... 查询逻辑 ...
    
    if not key.encrypted_key:
        raise ServerError(
            "该 API Key 是旧数据创建，不支持查看完整内容。"
            "建议删除此 Key 并重新创建一个新的 Key，新创建的 Key 将支持查看功能。"
        )
    
    decrypted_key = decrypt_api_key(key.encrypted_key)
    return BaseResponse(data={
        "id": str(key.id),
        "key_name": key.key_name,
        "api_key": decrypted_key,
        "key_prefix": key.key_prefix,
    })
```

#### 37.3.4 前端实现

在 API Keys 管理页面添加"查看"按钮：

```tsx
// web/src/pages/developer/Keys.tsx
const handleReveal = async (keyId: string) => {
    const data = await quotaApi.revealKey(keyId)
    setRevealKeyData(data)
    setRevealModalVisible(true)
}

// 表格操作列
{
    title: '操作',
    key: 'action',
    render: (_, record) => (
        <Space size="small">
            <Button icon={<EyeOutlined />} onClick={() => handleReveal(record.id)}>
                查看
            </Button>
            {/* 其他操作按钮 */}
        </Space>
    ),
}
```

---

### 37.4 相关文件

| 文件 | 修改内容 |
|------|---------|
| `src/models/api_key.py` | 添加 `encrypted_key` 字段 |
| `src/utils/crypto.py` | 添加 `encrypt_api_key()` 和 `decrypt_api_key()` |
| `src/api/v1/quota.py` | 添加 `/keys/{id}/reveal` 接口 |
| `requirements.txt` | 添加 `cryptography==42.0.2` |
| `web/src/api/quota.ts` | 添加 `revealKey()` API 方法 |
| `web/src/pages/developer/Keys.tsx` | 添加"查看"按钮和 Modal |

---

### 37.5 数据库迁移

新增迁移脚本 `migrations/add_encrypted_key.py`：

```bash
# 添加列
python migrations/add_encrypted_key.py

# 填充测试数据中的 key
# 脚本会自动识别并填充已知的测试 key
```

---

### 37.6 测试数据更新

测试数据库中的 API Keys 现在都支持查看功能：

| 用户 | Key 名称 | Key 前缀 | 完整 Key |
|------|----------|----------|----------|
| developer | 开发环境 Key | sk_test_a | sk_test_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |
| developer | 生产环境 Key | sk_live_A | sk_live_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA |
| test | 测试 Key | sk_test_b | sk_test_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb |

---

### 37.7 注意事项

1. **旧数据不兼容**：在功能添加之前创建的 Key 没有 `encrypted_key` 字段，无法查看明文
2. **安全建议**：
   - 建议用户创建 key 后立即保存
   - 定期轮换 key
   - 不要在代码仓库中存储 key

3. **加密密钥配置**：
   - 配置项：`api_key_encryption_secret`（在 `settings.py` 中统一管理）
   - 配置文件：`.env` 和 `.env.example`
   - 开发环境使用默认密钥
   - 生产环境必须修改为安全的随机密钥

   **密钥配置方式**：
   ```bash
   # .env 文件
   API_KEY_ENCRYPTION_SECRET=your-secure-random-secret-key
   ```

   **生产环境密钥生成**：
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

---

### 37.8 文档更新

此问题已更新至以下文档：

- `09_接口设计文档.md` - V2.3，新增 3.6.7 查看 API Key 明文接口
- `13_FAQ常见问题.md` - 新增 Q37 条目
- `scripts/init_db_with_data.py` - 更新测试数据，支持 encrypted_key
- `migrations/add_encrypted_key.py` - 新增迁移脚本

---

## 问题38：配额使用情况页面报错 AttributeError: '_isnull'

### 38.1 问题描述

打开"配额使用情况"页面时出现错误：

```
AttributeError: Neither 'Function' object nor 'Comparator' object has an attribute '_isnull'
```

错误堆栈指向：
- `quota.py` - get_quota_info 函数中 `Quota.user_id == current_user.id`
- `quota.py` - get_top_repos 函数中 `func.cast(KeyUsageLog.cost, type_=func.numeric)`

### 38.2 问题分析

**问题一**：`get_quota_info` 中直接查询 `Quota.user_id`，但：
- `Quota.user_id` 是 UUID 类型
- 与字符串 `current_user.id` 比较类型不匹配
- `Quota.user_id` 定义为 `not nullable=False`，用于查询不合理

**问题二**：`get_top_repos` 中 `func.cast()` 语法错误：
```python
func.cast(KeyUsageLog.cost, type_=func.numeric)  # ❌ 错误
```

### 38.3 解决方案

**修复一**：`get_quota_info` 函数
```python
# 首先验证 API Key 属于当前用户
key_result = await db.execute(
    select(APIKey).where(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    )
)

# 直接按 key_id 查询配额记录
quota_query = select(Quota).where(Quota.key_id == key_id)
```

**修复二**：`get_top_repos` 函数
```python
from sqlalchemy import Numeric  # 导入 Numeric 类型

# 修复 cast 语法
func.sum(func.cast(KeyUsageLog.cost, Numeric)).label("total_amount")  # ✅ 正确
```

### 38.4 涉及文件

- `src/api/v1/quota.py` - 修复 SQLAlchemy 查询语法

---

## 问题39：账单中心报错 function sum(character varying) does not exist

### 39.1 问题描述

打开"账单中心"页面时出现错误：

```
ERROR: 42703: function sum(character varying) does not exist
```

**错误提示**：
```
operator does not exist: sum(character varying)
HINT: No function matches the given name and argument types.
You might need to add explicit type casts.
```

**涉及接口**：`/api/v1/billing/monthly-summary`

**错误堆栈**：
```
File "...\src\api\v1\billing.py", line 213, in get_monthly_summary
    select(func.coalesce(func.sum(Bill.amount), 0))
```

### 39.2 问题分析

`Bill.amount` 字段在数据库中是 `VARCHAR(20)` 字符串类型，但代码直接使用 `func.sum(Bill.amount)` 进行求和操作。

PostgreSQL 不支持直接对字符串类型进行 `SUM()` 聚合运算，需要先将字符串转换为数值类型。

### 39.3 解决方案

在 `func.sum()` 中使用 `func.cast()` 将字符串转换为 `Numeric` 类型：

```python
from sqlalchemy import select, func, desc, Numeric  # 添加 Numeric 导入

# 修复前 (错误)
func.sum(Bill.amount)  # ❌ 字符串不能求和

# 修复后 (正确)
func.sum(func.cast(Bill.amount, Numeric))  # ✅ 先转换为数值类型
```

### 39.4 涉及文件

- `src/api/v1/billing.py` - 修复 `get_monthly_summary` 函数中的 `func.sum()` 调用

### 39.5 错误截图

<!-- 请将错误截图保存到 doc_images/faq39_error.png，然后取消下面这行的注释 -->
![账单中心报错截图](../doc_images/faq39_error.png)

---

## Q40: 账单中心按月统计报错：timestamp | string comparison not supported

### 40.1 问题描述

在账单中心的按月统计功能中，查询某月数据时可能遇到以下错误：

```
ERROR: timestamp | string comparison not supported
```

### 40.2 问题原因

在 `billing.py` 的 `get_monthly_summary` 函数中，使用字符串直接与 timestamp 类型字段比较：

```python
# 错误代码 - 使用字符串比较
start_date = f"{year}-{month:02d}-01"
end_date = f"{year}-{month+1:02d}-01" if month < 12 else f"{year+1}-01-01"

query = select(Bill).where(
    Bill.user_id == user_id,
    Bill.created_at >= start_date,  # 字符串与 timestamp 比较
    Bill.created_at < end_date       # 字符串与 timestamp 比较
)
```

PostgreSQL 不支持将字符串直接与 timestamp 类型进行大小比较。

### 40.3 解决方案

使用 `datetime` 对象替代字符串：

```python
from datetime import datetime

# 正确代码 - 使用 datetime 对象
start_date = datetime(year, month, 1)
if month == 12:
    end_date = datetime(year + 1, 1, 1)
else:
    end_date = datetime(year, month + 1, 1)

query = select(Bill).where(
    Bill.user_id == user_id,
    Bill.created_at >= start_date,  # datetime 与 timestamp 比较
    Bill.created_at < end_date       # datetime 与 timestamp 比较
)
```

### 40.4 涉及文件

- `src/api/v1/billing.py` - 修复 `get_monthly_summary` 函数中的日期比较

### 40.5 错误截图

<!-- 请将错误截图保存到 doc_images/faq40_error.png，然后取消下面这行的注释 -->
![账单中心timestamp比较错误截图](../doc_images/faq40_error.png)

---

## Q41: 日志管理功能使用指南

### 41.1 功能概述

管理员日志管理功能提供以下能力：

| 功能 | 说明 |
|------|------|
| 查看日志 | 分页查看日志内容，支持级别过滤和关键词搜索 |
| 导出日志 | 导出完整日志文件到本地 |
| 备份日志 | 手动备份指定模块的日志文件 |
| 查看备份 | 查看备份文件内容，支持过滤和搜索 |
| 下载备份 | 下载备份文件到本地 |
| 自动备份 | 文件超过大小限制时自动备份 |

### 41.2 日志文件说明

系统日志文件位置：`api-platform/logs/`

| 文件类型 | 路径 | 说明 |
|---------|------|------|
| 主日志 | `logs/server_api_platform_YYYYMMDD.log` | 系统主日志 |
| 模块日志 | `logs/modules/*.log` | 按模块分离的日志 |
| 备份文件 | `logs/backups/*.log` | 日志备份文件 |

### 41.3 日志格式

```
2026-04-19 01:00:00 | [SERVER] | INFO     | auth:123 | 用户登录成功
2026-04-19 01:00:01 | [SERVER] | ERROR    | billing:456 | 计费失败
```

| 字段 | 说明 |
|------|------|
| timestamp | 时间戳 |
| [SERVER] | 服务前缀 |
| LEVEL | 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL) |
| module:line | 模块名:行号 |
| message | 日志消息 |

### 41.4 常见问题

**Q: 为什么查看日志显示为空？**
A: 可能原因：
1. 日志文件不存在或路径错误
2. 日志格式与解析器不匹配（已修复）
3. 文件权限问题

**Q: 如何导出完整日志？**
A: 在日志文件列表中，点击对应文件的"导出"按钮即可下载完整日志。

**Q: 备份文件有什么用？**
A: 备份文件在日志文件超过配置大小限制时自动创建，可在备份列表中查看和下载。

### 41.5 涉及文件

- `src/api/v1/admin_logs.py` - 日志管理API
- `src/config/logging_config.py` - 日志配置和解析
- `web/src/pages/admin/AdminLogs.tsx` - 日志管理前端页面
- `web/src/api/adminLogs.ts` - 前端API客户端

---

## 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| V1.0 | 2026-04-18 | 初始版本，记录登录错误提示问题及解决方案 | AI Assistant |
| V1.1 | 2026-04-18 | 新增前端动态标题显示功能（问题33续） | AI Assistant |
| V1.2 | 2026-04-18 | 新增Q35：添加 username 和 role 字段，支持用户名登录和权限管理 | AI Assistant |
| V1.3 | 2026-04-18 | 新增Q36：前端统一响应格式问题 - Axios 拦截器自动提取 data 字段 | AI Assistant |
| V1.4 | 2026-04-19 | 新增Q37：添加查看 API Key 明文功能，包括加密存储、后端接口、前端实现、数据库迁移 | AI Assistant |
| V1.5 | 2026-04-19 | Q37补充：密钥配置改用 settings.py 统一管理，更新 .env 配置说明 | AI Assistant |
| V1.6 | 2026-04-19 | 新增Q38：配额使用情况页面报错修复 - SQLAlchemy 查询语法错误和 cast 语法问题 | AI Assistant |
| V1.7 | 2026-04-19 | 新增Q39：账单中心报错修复 - Bill.amount 字符串类型求和需要 cast 转换 | AI Assistant |
| V1.8 | 2026-04-19 | 新增Q40：账单中心按月统计报错 - timestamp 与 string 比较错误，需使用 datetime 对象 | AI Assistant |
| V1.9 | 2026-04-19 | 新增Q41：日志管理功能使用指南 - 查看/导出/备份功能说明及日志格式介绍 | AI Assistant |


---

**文档结束**

如有问题，请联系技术支持。
