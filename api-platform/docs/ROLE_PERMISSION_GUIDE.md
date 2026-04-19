# 用户角色权限系统设计文档

## 版本历史

| 版本 | 日期 | 作者 | 修改内容 |
|------|------|------|----------|
| v1.0 | 2024-04-19 | - | 初始版本，定义用户类型、角色和权限体系 |
| v1.1 | 2024-04-19 | AI | 更新普通用户界面菜单，区分 developer 和 user 权限，添加 DeveloperOnlyRoute 路由守卫 |

---

## 1. 用户类型 (User Type)

用户类型标识用户在平台中的**业务角色**，决定用户的功能入口和界面展示。

| 用户类型 | 标识 | 说明 | 登录后默认页面 |
|---------|------|------|---------------|
| 超级管理员 | `super_admin` | 平台最高权限，负责系统全局管理 | `/superadmin` |
| 管理员 | `admin` | 日常运营管理，用户和仓库管理 | `/admin` |
| 仓库所有者 | `owner` | API仓库的创建者和运营者 | `/owner` |
| 开发者 | `developer` | API服务的使用者 | `/` |
| 普通用户 | `user` | 基础功能用户 | `/` |

---

## 2. 角色 (Role)

角色标识用户在系统中的**权限级别**，用于权限控制。

| 角色 | 标识 | 说明 | 权限级别 |
|------|------|------|----------|
| 超级管理员 | `super_admin` | 拥有所有权限 | 4 (最高) |
| 管理员 | `admin` | 系统管理和用户管理 | 3 |
| 开发者 | `developer` | 基本使用权限 | 2 |
| 普通用户 | `user` | 受限权限 | 1 |

### 用户类型与角色的默认映射

| 用户类型 | 默认角色 | 说明 |
|---------|---------|------|
| super_admin | super_admin | 一一对应 |
| admin | admin | 一一对应 |
| owner | developer | 使用开发者权限，但有额外的仓库管理功能 |
| developer | user | 使用基础权限 |
| user | user | 一一对应 |

---

## 3. 权限 (Permission)

权限使用 `resource:action` 格式，支持通配符 `*` 表示所有权限。

### 权限分类

#### 3.1 用户管理权限
| 权限标识 | 说明 |
|---------|------|
| `user:read` | 查看用户信息 |
| `user:write` | 编辑用户信息 |
| `user:delete` | 删除用户 |
| `user:manage` | 管理所有用户 |
| `user:role` | 分配用户角色 |

#### 3.2 API Key 权限
| 权限标识 | 说明 |
|---------|------|
| `api:read` | 查看API Keys |
| `api:write` | 创建API Keys |
| `api:delete` | 删除API Keys |
| `api:manage` | 管理所有API Keys |

#### 3.3 仓库管理权限
| 权限标识 | 说明 |
|---------|------|
| `repo:read` | 查看仓库 |
| `repo:write` | 创建仓库 |
| `repo:delete` | 删除仓库 |
| `repo:approve` | 审核仓库 |
| `repo:manage` | 管理所有仓库 |

#### 3.4 账单管理权限
| 权限标识 | 说明 |
|---------|------|
| `billing:read` | 查看账单 |
| `billing:write` | 编辑账单 |
| `billing:manage` | 管理所有账单 |
| `billing:recharge` | 充值 |

#### 3.5 日志权限
| 权限标识 | 说明 |
|---------|------|
| `log:read` | 查看个人日志 |
| `log:all` | 查看所有日志 |

#### 3.6 系统管理权限
| 权限标识 | 说明 |
|---------|------|
| `system:settings` | 系统设置 |
| `system:logs` | 系统日志 |

#### 3.7 开发者功能权限
| 权限标识 | 说明 |
|---------|------|
| `dev:apikeys` | 管理自己的API Keys |
| `dev:quota` | 查看配额 |
| `dev:billing` | 个人账单 |

#### 3.8 仓库所有者功能权限
| 权限标识 | 说明 |
|---------|------|
| `owner:repo` | 管理自己的仓库 |
| `owner:analytics` | 数据分析 |
| `owner:settlement` | 收益结算 |

---

## 4. 角色默认权限

### 超级管理员 (super_admin)
```
拥有所有权限 (*)
```

### 管理员 (admin)
```
user:read, user:write, user:delete, user:manage,
api:read, api:manage,
repo:read, repo:approve, repo:manage,
billing:read, billing:manage,
log:all,
system:settings, system:logs
```

### 开发者 (developer)
```
dev:apikeys, dev:quota, dev:billing,
log:read, billing:read, repo:read
```

### 普通用户 (user)
```
dev:quota, billing:read, repo:read
```

---

## 5. 界面菜单对照

### 5.1 超级管理员界面 (`/superadmin`)

```
├── 工作台 (仪表板)
├── 全局用户 (用户管理)
├── 角色权限 (角色配置)
├── 系统配置 (系统设置)
└── 审计日志
```

### 5.2 管理员界面 (`/admin`)

```
├── 工作台 (仪表板)
├── 用户管理
├── 仓库管理
├── 日志管理
└── 系统设置
```

### 5.3 仓库所有者界面 (`/owner`)

```
├── 工作台
├── API Keys
├── 配额使用
├── 调用日志
├── 账单中心
─────────────────────────────────
├── 仓库管理
├── 数据分析
└── 收益结算
```

### 5.4 开发者界面 (`/`)

```
├── 工作台
├── API Keys
├── 配额使用
├── 调用日志
└── 账单中心
```

### 5.5 普通用户界面 (`/`)

> **注意**：普通用户界面与开发者界面不同，普通用户只能查看，不能创建 API Keys。

```
├── 工作台
├── 配额使用
└── 账单中心
```

> ⚠️ 普通用户没有以下功能：
> - API Keys 管理（不能创建/管理 API Keys）
> - 调用日志（不能查看 API 调用记录）

---

## 6. 路由权限控制

### 6.1 基础路由权限

| 路由 | 允许用户类型 | 必需权限 |
|------|------------|---------|
| `/` | developer, user | - |
| `/owner/*` | owner | owner:repo |
| `/admin/*` | admin | user:manage |
| `/superadmin/*` | super_admin | - |

### 6.2 开发者专属路由

| 路由 | 允许用户类型 | 说明 |
|------|------------|------|
| `/developer/keys` | **developer** | API Keys 管理，仅 developer 类型可访问 |
| `/developer/quota` | developer, user | 配额查看，所有登录用户可访问 |
| `/developer/logs` | developer, user | 调用日志查看 |
| `/developer/billing` | developer, user | 账单中心查看 |

### 6.3 路由守卫实现

**DeveloperOnlyRoute** - 开发者专属路由守卫：

```typescript
const DeveloperOnlyRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, user } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // 仅 developer 类型可以访问
  if (user && user.user_type !== 'developer') {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

// 使用方式
<Route path="keys" element={
  <DeveloperOnlyRoute>
    <DeveloperKeys />
  </DeveloperOnlyRoute>
} />
```

---

## 7. 测试账户

| 用户类型 | 用户名 | 邮箱 | 密码 | 角色 | 说明 |
|---------|--------|------|------|------|------|
| 超级管理员 | superadmin | superadmin@example.com | super123456 | super_admin | 最高权限 |
| 管理员 | admin | admin@example.com | admin123 | admin | 日常管理 |
| 仓库所有者 | owner | owner@example.com | owner123 | developer | 仓库运营 |
| 开发者 | developer | developer@example.com | dev123456 | user | 可创建 API Keys |
| 普通用户 | test | test@example.com | test123 | user | 只能查看 |

> **注意**：
> - `developer` 用户类型为 `developer`，可以创建 API Keys
> - `test` 用户类型为 `user`，只能查看，不能创建 API Keys

---

## 8. 实现文件

| 文件路径 | 说明 |
|---------|------|
| `web/src/config/permissions.ts` | 权限定义和配置 |
| `web/src/config/permissionHooks.ts` | 权限检查 Hooks |
| `web/src/components/Layout.tsx` | 根据用户类型显示不同菜单（userMenu/developerMenu） |
| `web/src/App.tsx` | 路由守卫（ProtectedRoute/DeveloperOnlyRoute）和权限控制 |
| `web/src/pages/superadmin/*` | 超级管理员页面 |
| `scripts/init_db_with_data.py` | 测试数据种子脚本 |

### 8.1 关键代码

**Layout.tsx - 用户菜单区分**：

```typescript
// 普通用户菜单
const userMenu = [
  { key: '/', label: '工作台' },
  { key: '/developer/quota', label: '配额使用' },
  { key: '/developer/billing', label: '账单中心' },
]

// 开发者菜单
const developerMenu = [
  { key: '/', label: '工作台' },
  { key: '/developer/keys', label: 'API Keys' },
  { key: '/developer/quota', label: '配额使用' },
  { key: '/developer/logs', label: '调用日志' },
  { key: '/developer/billing', label: '账单中心' },
]
```

**App.tsx - 路由守卫**：

```typescript
// 开发者专属路由
<Route path="keys" element={
  <DeveloperOnlyRoute>
    <DeveloperKeys />
  </DeveloperOnlyRoute>
} />
```

---

## 9. 安全考虑

1. **前端权限控制**：用于提升用户体验，但不可作为安全防线
2. **后端权限控制**：必须在API层面验证用户权限
3. **角色提升限制**：只有super_admin可以分配admin角色
4. **审计日志**：记录所有敏感操作
