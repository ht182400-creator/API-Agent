# 通用 API 服务平台（API Platform）

> **API 聚合中转站** —— 通过统一的入口、标准化的认证、智能的路由、统一的计费，把分散的第三方 API 仓库整合为"一次对接、全部可用"的一站式 API 服务。

| 项目信息 | 内容 |
|----------|------|
| 项目名称 | 通用 API 服务平台 / API Platform |
| 项目定位 | API 聚合中转站 + API 交易市场 |
| 后端技术 | Python 3.11+ / FastAPI / SQLAlchemy 2.0（异步） |
| 数据库 | PostgreSQL 15+ / Redis 7+ / MinIO |
| 前端技术 | React 18 + TypeScript 5 + Vite 5 + Ant Design 5 + Zustand |
| 部署方式 | Docker Compose / Kubernetes / Electron 桌面端 |
| 当前版本 | V1.0.0（文档包版本 V4.3） |
| 许可证 | MIT |

---

## 目录

- [一、项目简介](#一项目简介)
- [二、业务模式与核心价值](#二业务模式与核心价值)
- [三、核心特性](#三核心特性)
- [四、系统架构](#四系统架构)
- [五、技术栈](#五技术栈)
- [六、整体目录结构](#六整体目录结构)
- [七、后端模块说明](#七后端模块说明)
- [八、前端模块说明](#八前端模块说明)
- [九、角色权限体系](#九角色权限体系)
- [十、数据库设计](#十数据库设计)
- [十一、API 接口清单](#十一api-接口清单)
- [十二、SDK 与工具链](#十二sdk-与工具链)
- [十三、快速开始](#十三快速开始)
- [十四、部署](#十四部署)
- [十五、测试](#十五测试)
- [十六、开发规范](#十六开发规范)
- [十七、外网穿透配置](#十七外网穿透配置)
- [十八、文档索引](#十八文档索引)
- [十九、常见问题（FAQ）](#十九常见问题faq)
- [二十、许可证](#二十许可证)

---

## 一、项目简介

通用 API 服务平台是一个 **API 聚合中转站**。它把原本分散、认证方式各异、计费口径不一的第三方 API，统一收敛到一个平台：

- 开发者只对接平台一次，即可调用平台上所有仓库（Repository）；
- 平台统一负责认证、限流、路由、转发、计费、配额、日志、对账；
- 仓库方（Owner）专注提供 API 能力，由平台负责流量导入与收益结算。

平台同时是一套 **API 交易市场**：仓库方发布 API 产品 → 管理员审核上线 → 开发者订阅调用 → 平台按量计费 → 定期与仓库方结算。

---

## 二、业务模式与核心价值

### 2.1 传统模式 vs 平台模式

| 维度 | 传统模式 | 平台模式 |
|------|----------|----------|
| 对接方式 | 每个仓库单独对接 | 一次对接，调用所有 |
| 认证 | 各仓库各不相同 | 统一 API Key + HMAC 签名 |
| 计费 | 无统一口径 | 统一计费与配额 |
| 监控 | 分散、缺失 | 统一日志 / 统计 / 告警 |
| 维护成本 | 高 | 低 |

### 2.2 各角色价值

| 角色 | 痛点 | 平台解决方案 |
|------|------|-------------|
| **开发者（Developer）** | 对接多个仓库耗时 | 一次对接，调用所有 |
| **仓库方（Owner）** | 获客难、计费难 | 流量导入 + 分成结算 |
| **平台方（Platform）** | — | 抽取佣金 + 增值服务 |

---

## 三、核心特性

- **统一入口**：一个 API Key 调用所有仓库
- **统一认证**：JWT（用户侧）+ API Key + HMAC 签名（开放 API）
- **统一计费**：账户余额、账单、月度账单、充值、退款全链路
- **热插拔**：仓库可动态接入、审核、上下线
- **多协议适配**：HTTP 适配器已实现（gRPC 适配器预留）
- **在线支付**：支付宝沙箱/生产（PC 网页支付 + 扫码支付），微信/银行卡配置就绪待实现
- **对账系统**：定时对账、长短款差异、平台账户、对账报表
- **审计与操作日志**：审计日志（AuditLog）+ 用户操作日志（UserOperationLog）
- **通知中心**：站内信、通知偏好、广播
- **多端支持**：Web 控制台 + Electron 桌面端 + Python/JS SDK
- **高性能目标**：10,000 QPS / P99 < 500ms

---

## 四、系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         接入层 (Gateway)                              │
│     HTTPS 证书  │   WAF 防护   │   限流控制   │   路由分发              │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          认证层 (Auth)                                │
│     API Key 验证  │  JWT Token  │  HMAC 签名  │   权限控制            │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      业务逻辑层 (Core Services)                       │
│  路由引擎 │ 协议转换 │ 限流引擎 │ 计费引擎 │ 插件管理 │ 监控日志 │ SDK │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  仓库适配层    │      │    数据层      │      │   外部服务     │
│ HTTP 适配器    │      │ PostgreSQL     │      │  仓库节点 A    │
│ gRPC 代理      │      │ Redis          │      │  仓库节点 B    │
│ 自定义协议     │      │ MinIO          │      │  更多仓库...   │
└───────────────┘      └───────────────┘      └───────────────┘
```

### 4.1 API 调用完整流程

```
开发者 ─▶ ① 认证 ─▶ ② 限流 ─▶ ③ 路由 ─▶ ④ 计费 ─▶ ⑤ 调用仓库 ─▶ ⑥ 返回
            │          │          │          │
            ▼          ▼          ▼          ▼
        验证Key    检查配额    转发请求    记录日志/扣费
        JWT验证    熔断降级    协议转换    更新统计
```

### 4.2 请求链路（后端实现）

1. `RequestLoggingMiddleware` 注入 `X-Request-ID` / `X-Process-Time`
2. 依赖注入 `get_current_user`（JWT）或 `verify_api_key`（API Key）完成认证
3. `AuthService._check_rate_limit` 查询 `APICallLog` / `Quota` 做限流与配额校验
4. `RepoService.call_repository` 选择适配器、构建认证头、转发请求
5. 记录 `APICallLog`，`BillingService` 完成扣费
6. 统一响应包装为 `{ code, message, data, request_id }`

---

## 五、技术栈

### 5.1 后端

| 分类 | 技术 | 版本 |
|------|------|------|
| Web 框架 | FastAPI | 0.109.2 |
| ASGI 服务器 | uvicorn[standard] | 0.27.1 |
| 数据校验 | Pydantic / pydantic-settings | 2.6.1 / 2.1.0 |
| ORM | SQLAlchemy | 2.0.25 |
| 数据库驱动 | asyncpg / psycopg2-binary | 0.29.0 / 2.9.9 |
| 迁移 | Alembic | 1.13.1 |
| 缓存 | redis / aioredis | 5.0.1 / 2.0.1 |
| 认证安全 | python-jose / passlib[bcrypt] / cryptography | 3.3.0 / 1.7.4 / 42.0.2 |
| HTTP 客户端 | httpx / aiohttp | 0.26.0 / 3.9.3 |
| 日志 | structlog | 24.1.0 |
| 监控 | prometheus-client | 0.19.0 |
| 支付 | alipay-sdk-python / qrcode | 3.7.865 / 7.4.2 |

### 5.2 前端

| 分类 | 技术 | 版本 |
|------|------|------|
| 框架 | React / React DOM | 18.2.0 |
| 语言 | TypeScript | 5.3.0 |
| 构建 | Vite | 5.0.0 |
| UI | Ant Design + @ant-design/icons | 5.12.0 / 5.2.6 |
| 状态管理 | Zustand（+ persist） | 4.4.0 |
| 路由 | react-router-dom | 6.20.0 |
| HTTP | Axios | 1.6.0 |
| 图表 | ECharts / echarts-for-react / Recharts | 5.4.0 / 3.0.0 / 2.10.0 |
| 国际化 | i18next / react-i18next | 23.7.0 / 14.0.0 |
| 日期 | dayjs | 1.11.10 |
| 测试 | @playwright/test | 1.59.1 |
| 规范 | ESLint / Prettier | 8.55.0 / 3.1.0 |

### 5.3 基础设施

| 组件 | 版本 | 用途 |
|------|------|------|
| PostgreSQL | 15-alpine | 主数据库 |
| Redis | 7-alpine | 缓存 / 限流 |
| MinIO | latest | 对象存储 |
| Nginx | alpine | 反向代理 |
| Prometheus + Grafana | latest | 监控（可选 profile） |

---

## 六、整体目录结构

```
API-Agent/
├── README.md                       # 本文件：项目总 README
├── Icon.png / mainscreen.png       # 项目图标与界面截图
│
├── api-platform/                   # ★ 后端 + Web 前端主工程
│   ├── src/                        # 后端源码（FastAPI）
│   ├── web/                        # Web 控制台前端（React + Vite）
│   ├── sdk/                        # 官方 SDK（Python / JS）
│   ├── migrations/                 # 数据库迁移脚本（Alembic + 手写）
│   ├── scripts/                    # 初始化 / 种子 / 校验 / 迁移脚本
│   │   ├── convert_key.py          #   支付宝私钥 PKCS1 格式转换（正式工具）
│   │   ├── run_test.ps1            #   测试运行封装
│   │   └── dev/                    #   开发调试脚本归档（不参与运行与单测）
│   ├── docker/                     # Dockerfile / docker-compose
│   ├── docs/                       # 工程级文档（测试、日志、支付、角色、优化跟踪）
│   ├── tests/                      # 后端测试
│   ├── config/                     # 日志等配置
│   ├── keys/                       # 密钥目录（支付宝等）
│   ├── Makefile                    # 常用命令入口
│   ├── requirements.txt            # 生产依赖
│   ├── requirements-dev.txt        # 开发依赖
│   ├── pyproject.toml / pytest.ini # 工程配置
│   └── README.md                   # 后端工程 README
│
├── electron/                       # ★ Electron 桌面端（一键部署包）
│   ├── main.js / preload.js
│   ├── build/                      # 图标 + NSIS 安装脚本
│   ├── dependencies/               # 内置 Docker Desktop 安装器
│   └── package.json
│
├── OwnerServer/                    # ★ 仓库方（Owner）开发指南 + 示例 API
│   ├── README.md                   # Owner 开发指南
│   └── weather-api/                # 完整示例天气 API 产品（FastAPI，端口 8001）
│
├── Developer/                      # ★ 开发者示例与测试工具
│   ├── API测试工具/                # API 测试工具设计文档
│   └── CallWeatherTest Tool/       # 可运行纯前端天气测试工具
│
├── mobil-web/                      # ★ 移动端移植方案文档（暂无代码）
│   └── doc/                        # 移动端适配方案说明书
│
├── Doc/                            # ★ 平台级项目文档（40+ 篇）
│   ├── 00_文档索引.md
│   ├── 01_项目需求规格说明书.md
│   ├── 08_数据库设计文档.md
│   ├── 09_接口设计文档.md
│   ├── 18_通用API服务平台架构.md
│   ├── 19_UI设计文档_竹韵赛博风.md
│   └── 33~41_开发过程中的FAQ_更新*.md
│
└── 通用API服务平台文档/             # ★ 对外发布版文档（md + docx）
    ├── 00_文档索引.md
    ├── 19~27_需求/方案/周期/SOW/验收/风险/改进/DB/接口
    ├── 29~33_上手指南 / 快速开始 / SDK 手册 / 故障排查 / 环境FAQ
    └── *.py                        # 文档转换脚本
```

---

## 七、后端模块说明

### 7.1 源码结构 `api-platform/src/`

```
src/
├── main.py             # FastAPI 应用入口：lifespan、异常处理器、中间件、路由挂载
├── config/             # 配置模块
│   ├── settings.py     #   应用配置（DB/Redis/JWT/CORS/限流/支付/计费/加密）
│   ├── database.py     #   异步 + 同步引擎、Session、Base、get_db 依赖
│   └── logging_config.py # 多级别日志、按模块分文件、自动备份
├── core/               # 核心模块
│   ├── exceptions.py   #   完整异常层级与业务错误码
│   ├── middleware.py   #   请求日志中间件、CORS、限流占位
│   └── security.py     #   密码哈希、API Key 生成/哈希、JWT、HMAC 签名
├── api/
│   ├── __init__.py     #   顶层路由聚合
│   └── v1/             #   API v1（见第十一章）
├── models/             # 数据模型（SQLAlchemy，见第十章）
├── services/           # 业务服务（见 7.3）
├── adapters/           # 协议适配器
│   ├── base.py         #   BaseAdapter 抽象基类 + 请求/响应数据类
│   ├── http_adapter.py #   HTTP 适配器（httpx，超时/重试/认证头/签名）
│   └── grpc_adapter.py #   gRPC 适配器（占位）
├── schemas/            # Pydantic 请求/响应模型
│   ├── request.py      #   请求模型
│   └── response.py     #   响应模型（BaseResponse / PaginatedResponse ...）
└── utils/              # 工具函数
    ├── crypto.py       #   Fernet 加密、哈希、随机串、request_id
    └── helpers.py      #   IP / UA 解析、UTC 时间、邮箱校验等
```

### 7.2 核心模块职责

| 模块 | 职责 |
|------|------|
| `config/settings.py` | 全局配置，含 CORS 解析、支付宝密钥读取，`get_settings()` 带缓存 |
| `config/database.py` | 异步引擎（asyncpg）+ 同步引擎（psycopg2），`get_db()` 自动 commit/rollback 并设置 UTC 时区 |
| `config/logging_config.py` | 模块化日志、自动备份与清理（`logs/modules/`、`logs/backups/`） |
| `core/exceptions.py` | `APIError` 基类及 20+ 业务异常（错误码分段：401xx / 403xx / 429xx / 400xx / 5xxxx） |
| `core/security.py` | bcrypt/sha256 密码哈希、`sk_live_` API Key、JWT 签发校验、HMAC 签名（5 分钟容差防重放） |
| `core/middleware.py` | 请求 ID / 耗时注入、分级日志、CORS |

### 7.3 业务服务 `src/services/`

| 服务 | 关键能力 |
|------|----------|
| `AuthService` | JWT 依赖注入、API Key 校验、RPM/RPH/配额/余额检查、HMAC 验签、Key 生命周期管理 |
| `RepoService` | 仓库 CRUD、`call_repository` 网关转发、认证头构建、调用日志与计费触发 |
| `BillingService` | 账户、充值、消费、冻结/解冻、退款、账单、余额历史、月度汇总、向 Owner 结算 |
| `AccountService` | 账户获取/创建（唯一约束并发安全）、余额增减、冻结、账单历史 |
| `QuotaService` | 配额检查、消费、设置、重置、使用历史、Top 仓库、免费额度 |
| `PaymentService` | 套餐、下单（套餐/自定义金额）、支付宝网页支付与扫码、主动查询补偿、回调幂等处理、充值后自动升级、取消/退款 |
| `NotificationService` | 通知 CRUD、未读数、已读、偏好、系统/账单/安全通知 |
| `PermissionService` | 统一角色判断（`UserRole` 枚举）、`can_create_repo`、`has_permission`（`*` 通配） |
| `ReconciliationScheduler` | 定时对账（APScheduler 每日 04:00）、长短款差异、对账状态 |

---

## 八、前端模块说明

### 8.1 目录结构 `api-platform/web/src/`

```
web/src/
├── main.tsx        # 入口：ReactDOM + BrowserRouter + antd ConfigProvider(zhCN)
├── App.tsx         # ★ 路由中心：所有路由 + ProtectedRoute 路由守卫
├── index.css       # 全局样式
├── api/            # API 客户端（client.ts 统一 axios + 各业务模块）
├── components/     # 公共组件（Layout、ErrorModal、ResponsiveTable、api-tester/*）
├── config/         # 权限模型、仓库元数据配置（permissions.ts / repos/）
├── contexts/       # React Context（ErrorContext 全局错误处理）
├── hooks/          # useApi / useDevice
├── pages/          # 页面（按角色分目录，见 8.3）
├── stores/         # Zustand 状态（auth / app / apiKey）
├── styles/         # 独立 CSS（断点、赛博主题、支付样式）
├── types/          # TS 类型（api-tester.ts）
└── utils/          # logger.ts / paymentErrors.tsx
```

> 说明：**项目不存在独立的 `src/router` 目录**，所有路由与守卫集中在 `App.tsx`；`config/permissions.ts` 提供另一套权限常量与 Hook。

### 8.2 前端 API 客户端

统一封装在 `src/api/client.ts`：

- 基础地址：`import.meta.env.VITE_API_URL || '/api/v1'`（开发经 Vite 代理到 `http://localhost:8000`）
- 请求拦截器：自动注入 `Authorization: Bearer <token>`，记录请求日志
- 响应拦截器：自动解包后端统一响应 `{ code, message, data }` → 直接返回 `data`；状态码映射中文 `userMessage`；**401 且非 `/auth/` 接口自动登出**
- 导出：`api.get/post/put/delete/patch`、`ApiResponse` / `PaginatedResponse` 类型

业务 API 模块（`src/api/*.ts`）：`auth`、`repo`、`billing`、`quota`、`payment`、`analytics`、`notification`、`user`、`admin`、`adminAnalytics`、`adminLogs`、`adminPricingConfig`、`adminReconciliation`、`superadmin`。

### 8.3 页面清单（按角色）

**公开页面**

| 路由 | 说明 |
|------|------|
| `/login` | 登录 |
| `/register` | 注册 |
| `/payment-success` | 支付结果页 |

**开发者端 `/`（user_type: developer / owner）**

| 路由 | 说明 |
|------|------|
| `/` | 开发者工作台 |
| `/developer/keys` | API Key 管理 |
| `/developer/repos` `/developer/repos/:slug` | 仓库市场 / 详情 |
| `/developer/create-repo` | 创建仓库 |
| `/developer/quota` | 配额使用 |
| `/developer/logs` | 调用日志 |
| `/developer/billing` | 账单中心 |
| `/developer/usage` `/developer/consumption-details` | 使用概览 / 消费明细 |
| `/developer/recharge` | 充值中心 |
| `/developer/api-tester` | 在线 API 测试工具 |

**仓库所有者端 `/owner/*`（owner / developer / admin）**

| 路由 | 说明 |
|------|------|
| `/owner` | 所有者工作台 |
| `/owner/repos` | 仓库管理（创建/编辑/上下线） |
| `/owner/analytics` | 数据分析 |
| `/owner/settlement` | 收益结算 |

**管理员端 `/admin/*`（admin）**

| 路由 | 说明 |
|------|------|
| `/admin` | 管理工作台 |
| `/admin/users` | 用户管理 |
| `/admin/repos` | 仓库审核与管理 |
| `/admin/logs` | 日志管理（文件/内容/统计/备份） |
| `/admin/settings` | 系统设置 |
| `/admin/devtools` | 开发者调试工具 |
| `/admin/recharge-records` | 充值明细 |
| `/admin/channel-summary` | 渠道收款汇总 |
| `/admin/platform-accounts` | 平台账户余额 |
| `/admin/reconciliation` | 对账管理 |
| `/admin/pricing-config` | 计费规则管理 |
| `/admin/monthly-bills` | 月度账单管理 |
| `/admin/analytics` | 运营数据分析 |

**超级管理员端 `/superadmin/*`（super_admin）**

| 路由 | 说明 |
|------|------|
| `/superadmin` | 超管工作台 / 审计 |
| `/superadmin/users` | 全局用户管理 |
| `/superadmin/roles` | 角色权限管理 |
| `/superadmin/system` | 系统配置 |

**普通用户端 `/user/*`（user）**：`/user`、`/user/repos`、`/user/quota`、`/user/billing`、`/user/recharge`

**通用**：各角色 `/notifications` 通知中心

### 8.4 状态管理（Zustand）

| Store | Hook | 持久化 | 内容 |
|-------|------|--------|------|
| `auth.ts` | `useAuthStore` | ✅ `auth-storage` | user / accessToken / refreshToken / isAuthenticated |
| `app.ts` | `useAppStore` | ❌ | 侧边栏折叠、全局 loading / message |
| `apiKey.ts` | `useApiKeyStore` | ✅ `api-key-storage` | API 测试工具的 API Key |

---

## 九、角色权限体系

### 9.1 用户类型（User Type）

标识用户的**业务角色**，决定功能入口与界面。

| 用户类型 | 标识 | 说明 | 默认路径 |
|---------|------|------|----------|
| 超级管理员 | `super_admin` | 平台最高权限 | `/superadmin` |
| 管理员 | `admin` | 日常运营管理 | `/admin` |
| 仓库所有者 | `owner` | API 仓库创建者与运营者 | `/owner` |
| 开发者 | `developer` | API 服务使用者 | `/` |
| 普通用户 | `user` | 基础功能用户 | `/user` |

> **V4.0 起**：`owner` 不再是独立数据库角色，而是 `developer + 拥有仓库` 的业务状态；系统以 `user_type` 字段为准，`role` 字段保留兼容。

### 9.2 角色与权限

- 角色（Role）：`super_admin` / `admin` / `developer` / `user`（存于 `roles` 表，含 `permissions` JSONB）
- 权限格式：`resource:action`，如 `user:read`、`repo:approve`、`billing:recharge`；`*` 表示全部
- 统一由 `PermissionService` 校验：`is_admin()` / `is_super_admin()` / `is_developer()` / `can_create_repo()` / `has_permission()`

### 9.3 用户类型 → 默认角色映射

| 用户类型 | 默认角色 |
|---------|---------|
| super_admin | super_admin |
| admin | admin |
| owner | developer（+ 额外仓库管理功能） |
| developer | user |
| user | user |

---

## 十、数据库设计

> 主键统一使用 UUID；金额字段使用 `Numeric` / `Decimal`；大量使用 JSONB 承载扩展字段；全局使用 **UTC** 时间。

### 10.1 核心表清单（约 30+ 张）

**用户与权限**

| 表名 | 说明 |
|------|------|
| `users` | 用户主表（user_type / user_status / role / permissions / vip_level / 试用 / oauth） |
| `user_profiles` | 用户档案（昵称/头像/计费类型/信用额度/MFA） |
| `api_keys` | API Key（哈希存储、IP/仓库白名单、限流、配额、余额开关、过期） |
| `roles` | 角色与权限定义（含 `DEFAULT_ROLES`、`PERMISSION_DEFINITIONS`） |
| `audit_logs` | 审计日志（操作、资源、新旧数据、状态，复合索引） |
| `user_operation_logs` | 用户操作日志（页面、端点、请求数据、新旧值） |

**仓库与适配**

| 表名 | 说明 |
|------|------|
| `repositories` | 仓库主表（状态 pending/approved/rejected/online/offline、SLA、审核人） |
| `repo_configs` | 仓库配置（路由/认证/限流/转换） |
| `repo_pricing` | 仓库定价（按次/按量/包月/年、免费额度、套餐） |
| `repo_endpoints` | 仓库端点（路径、方法、请求/响应 schema、限流） |
| `repo_limits` | 仓库限流（rpm/rph/rpd、突发、并发、超时） |
| `repo_stats` | 仓库统计（小时级调用、延迟分位、成本） |
| `adapters` / `adapter_instances` | 适配器与实例（配置、能力、健康状态） |

**计费与账单**

| 表名 | 说明 |
|------|------|
| `accounts` | 账户（余额/赠金/代金券，唯一约束 `user_id+account_type`） |
| `bills` | 账单流水（充值/消费/退款/赠送/结算，含环境、支付方式） |
| `quotas` | 配额（rpm/rph/daily/monthly，已用/剩余、重置策略） |
| `api_call_logs` | API 调用日志（请求 ID、耗时、tokens、成本、来源、IP/UA） |
| `monthly_bills` | 月度账单（年/月、环境、收支、期初/期末余额、审核/发布状态） |
| `key_usage_logs` | Key 使用日志 |
| `pricing_configs` | 计费规则配置（可空 repo_id=全局；`calculate_cost()` 业务方法） |

**支付与对账**

| 表名 | 说明 |
|------|------|
| `payments` | 支付订单（支付号、类型、金额、渠道、状态、三方交易号、回调） |
| `recharge_packages` | 充值套餐（原价/售价/折扣、赠送、包含次数/tokens、有效期） |
| `payment_callbacks` | 支付回调记录（请求/响应体、验签、处理结果、重试） |
| `platform_accounts` | 平台渠道账户（渠道、账号、余额） |
| `reconciliation_records` | 对账记录（平台/渠道笔数与金额、匹配/长款/短款、差异） |
| `reconciliation_disputes` | 对账差异（长款/短款/金额差、处理状态与处理人） |

**系统与通知**

| 表名 | 说明 |
|------|------|
| `system_configs` | 系统配置（分类/键、值类型、加密标记、选项、是否可编辑） |
| `notifications` / `notification_preferences` | 通知与通知偏好（软删除） |

> 详细字段、索引、ER 图见 `Doc/08_数据库设计文档.md`。

---

## 十一、API 接口清单

> 统一前缀 `/api/v1`。响应格式：`{ "code": 0, "message": "success", "data": {...}, "request_id": "..." }`。

### 11.1 认证 `/auth`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/signature` | 生成 HMAC 签名 |
| POST | `/auth/register` | 注册 |
| POST | `/auth/login` | 登录（返回 access + refresh） |
| POST | `/auth/refresh` | 刷新 Token |
| GET | `/auth/me` | 当前用户信息 |
| POST | `/auth/logout` | 登出 |

### 11.2 仓库 `/repositories`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/repositories` | 仓库列表 |
| GET | `/repositories/my` | 我的仓库 |
| GET | `/repositories/{repo_slug}` | 仓库详情 |
| GET | `/repositories/{repo_id}/stats` | 仓库统计 |
| POST | `/repositories` | 创建仓库（默认 pending） |
| PUT/DELETE | `/repositories/{repo_id}` | 更新 / 删除 |
| POST | `/repositories/{repo_slug}/chat` `/translate` `/recognize` | 业务调用示例 |
| GET | `/repositories/admin/all` | 管理员：全部仓库 |
| POST | `/repositories/{repo_id}/approve` | 审核通过 |
| POST | `/repositories/{repo_id}/reject` | 审核拒绝 |
| POST | `/repositories/{repo_id}/online` `/offline` | 上线 / 下线 |
| GET/POST/PUT/DELETE | `/repositories/{repo_id}/endpoints...` | 端点管理 |
| GET/PUT | `/repositories/{repo_id}/limits` | 限流配置 |
| PUT | `/repositories/{repo_id}/config` | 完整配置更新 |

### 11.3 配额与 Key `/quota`

`GET/POST /quota/keys`、`GET/PUT/DELETE /quota/keys/{key_id}`、`POST /quota/keys/{key_id}/disable|enable|set-quota`、`GET /quota/keys/{key_id}/reveal`、`GET /quota/info/{key_id}`、`GET /quota/overview`、`GET /quota/logs`、`GET /quota/usage-history/{key_id}`、`GET /quota/consumption-trend`、`GET /quota/top-repos/{key_id}`

### 11.4 计费 `/billing`

`GET /billing/account`、`POST /billing/recharge`、`GET /billing/bills`、`GET /billing/bills/export`、`GET /billing/monthly-summary`、`GET /billing/balance-history`、`GET /billing/consumption-trend`、`GET /billing/usage`、`GET /billing/consumption-details`、`GET /billing/monthly-bills[...]`

### 11.5 支付 `/payments`

`GET /payments/config`、`GET /payments/packages[...]`、`POST /payments/custom`、`POST /payments/create`、`GET /payments/status/{payment_no}`、`POST /payments/refresh-qrcode/{payment_no}`、`POST /payments/cancel/{payment_no}`、`GET /payments/records`、`GET /payments/alipay/return`（302 跳转前端）、`POST /payments/alipay/callback`（RSA 验签）、`POST /payments/callback`、`POST /payments/refund/{payment_no}`

### 11.6 用户 / 升级 / 试用 `/user`

`GET /user/config`、`GET /user/status`、`GET /user/has-repos`、`POST /user/upgrade`、`POST /user/upgrade-with-payment`、`GET /user/upgrade-info`、`POST /user/claim-trial`

### 11.7 通知 `/notifications`

`GET /notifications`、`GET /notifications/unread-count`、`GET /notifications/recent`、`POST /notifications/{id}/read`、`POST /notifications/read-all`、`DELETE /notifications/{id}`、`DELETE /notifications/read/delete-all`、`GET/PUT /notifications/preferences`、`POST /notifications/broadcast`

### 11.8 日志与分析

- `/logs`：调用日志（分页）
- `/analytics/overview` `/trend` `/repo-details` `/repo/{repo_id}/trend` `/user-ranking` `/repo-ranking`

### 11.9 管理端接口

| 前缀 | 能力 |
|------|------|
| `/admin/logs` | 日志文件/内容/统计/备份/清理/配置/导出 |
| `/admin/users` `/admin/dashboard/stats` | 用户与仪表盘 |
| `/admin/billing` | 账户、用量、月度账单生成/审核/发布 |
| `/admin`（对账） | 充值记录、渠道汇总、平台账户、对账执行/结果/差异/报表/调度器 |
| `/admin/payment-config` | 支付配置状态/详情/更新/测试 |
| `/admin/pricing-configs` | 计费规则 CRUD / 成本试算 |
| `/superadmin` | 仪表盘、用户、审计日志、角色、权限、系统配置 |

---

## 十二、SDK 与工具链

### 12.1 官方 SDK（`api-platform/sdk/`）

| 语言 | 状态 | 关键文件 |
|------|------|----------|
| Python | ✅ 已发布 | `python/api_platform/{client,http_client,exceptions,utils}.py` |
| JavaScript / TypeScript | ✅ 已发布 | `js/src/{client,httpClient,exceptions,index}.ts` |
| Go | 🔧 开发中 | — |
| Java | 🔧 开发中 | — |
| PHP | 📋 计划中 | — |

SDK 能力：认证（API Key + HMAC 签名）、请求封装、响应解析、错误映射（401/429/404/400/5xx）、**指数退避重试**。

### 12.2 关联工程

| 目录 | 说明 |
|------|------|
| `electron/` | Electron 27 + electron-builder，将平台打包为 Windows/macOS/Linux 桌面应用，内置 Docker 自动安装与健康检查，用于私有化/离线交付 |
| `OwnerServer/` | 仓库方开发指南 + `weather-api` 完整示例产品（FastAPI，端口 8001） |
| `Developer/` | API 测试工具设计文档 + `CallWeatherTest Tool`（可运行纯前端天气测试工具） |
| `mobil-web/` | 移动端移植方案文档集（暂无可运行代码） |

---

## 十三、快速开始

### 13.1 环境要求

- Python 3.11+
- Node.js 18+ / npm 9+
- Docker Desktop 4.0+（PostgreSQL 15 / Redis 7 / MinIO）
- Windows / macOS / Linux

### 13.2 一键启动（Windows 批处理，推荐）

`api-platform/` 根目录提供两个批处理文件，**双击即可启动，且启动前会自动结束旧的同名服务进程**：

| 文件 | 作用 | 访问地址 |
|------|------|----------|
| `start-backend.bat` | 结束旧后端进程 → 启动 FastAPI（uvicorn，监听 8000） | http://localhost:8000/docs |
| `start-frontend.bat` | 结束旧 Vite 进程 → 启动前端（`npm run dev`，端口 3000 起自动探测） | http://localhost:3000 |

**启动顺序**：先 `start-backend.bat`，再 `start-frontend.bat`（前端 `/api` 由 Vite 代理到 8000）。

**杀进程策略（避免误杀）**：

- 后端：按命令行精确匹配 `uvicorn` / `src.main`，并连带结束其子进程（uvicorn `--reload` 的 Windows 工作进程）；
- 前端：按命令行匹配 `vite` + `api-platform`，精确定位本项目的 Vite 进程；
- 兜底：后端额外释放被占用的 8000 端口；
- 两者均只影响本项目进程，不会误杀其他 Python / Node 程序。

脚本还会做环境自检（`python` / `npm` 是否存在、`src/main.py` / `package.json` 是否存在、前端 `node_modules` 是否已安装），并统一设置 UTF-8 输出避免中文乱码。

### 13.3 后端启动

```bash
cd api-platform

# 1. 创建虚拟环境
python -m venv venv
# Windows PowerShell
.\venv\Scripts\Activate.ps1
# Linux / macOS
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动依赖服务（PostgreSQL / Redis / MinIO）
cd docker
docker-compose up -d postgres redis

# 4. 配置环境变量（数据库连接、JWT 密钥、支付宝等）
#    在 api-platform/ 下创建 .env

# 5. 初始化数据库（建表 + 初始化数据）
cd ..
python scripts/init_db_with_data.py --drop

# 6. 启动后端
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

- 健康检查：`http://localhost:8000/health`
- 就绪探针：`http://localhost:8000/ready`（校验 DB/Redis 依赖，未就绪返回 503）
- Swagger UI：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`

> `/health` 为**存活**探针（仅表示进程在运行）；`/ready` 为**就绪**探针（DB 必需，Redis 默认非强依赖，见 `READY_REQUIRE_REDIS`）。

### 13.4 前端启动

```bash
cd api-platform/web
npm install
npm run dev      # 默认从 3000 端口起自动探测，代理 /api → localhost:8000
```

浏览器访问 `http://localhost:3000`。

### 13.5 测试账号

| 账号 | 密码 | 用户类型 |
|------|------|----------|
| `superadmin` | `super123456` | 超级管理员 |
| `admin` | 见初始化脚本 | 管理员 |
| `developer` | 见初始化脚本 | 开发者 |

> 具体账号以 `scripts/init_db_with_data.py` 实际初始化为准。

### 13.6 环境隔离与支付模式（重要）

平台同时支持**模拟支付（测试）**与**真实支付（生产）**两套运行态，通过环境分层 + 启动强校验 + 数据隔离实现"模拟可测、生产安全"。

| 环境 | `ENVIRONMENT` | `PAYMENT_MOCK_MODE` | `ALIPAY_SANDBOX` | 说明 |
|------|---------------|---------------------|------------------|------|
| 本地/开发 | `development` | `true` | `true` | 自由模拟 |
| 预发/联调 | `staging` | `true` | `true` | **模拟测试正式试验场** |
| 生产 | `production` | `false` | `false` | 真实支付，启动强校验 |

**生产环境启动强校验（fail-fast）**：若 `ENVIRONMENT=production` 而模拟支付/沙箱/默认密钥未更换，服务将**拒绝启动**并列出全部风险项。

**账单环境隔离**：账单按 `environment`（`simulation` / `production`）隔离，
取值**由 `ENVIRONMENT` 决定**（`production`/`prod` → `production`，其余 → `simulation`），
**与 `PAYMENT_MOCK_MODE` 解耦** —— 关闭模拟支付只表示"不放行模拟回调"，不代表账单属于生产数据。
查询默认只看当前环境，支持显式跨环境查询：

```bash
GET /api/v1/billing/bills                      # 当前环境
GET /api/v1/billing/bills?environment=all      # 模拟 + 真实全部（排查/对账）
```

**支付回调门控**：

| 环境 | 通用回调 `/payments/callback` |
|------|-------------------------------|
| 生产 | 404（已下线；真实支付走 `/payments/alipay/callback`，含 RSA 验签） |
| 非生产 | 需登录（JWT）或携带 `X-Internal-Token`，并校验订单归属 |

**环境可见性与防漏传（L1~L5）**：账单环境错误属于"静默失败"（不报错、只是落进另一个环境 → 对账漏账），因此建立了五层防御：

| 层 | 措施 |
|----|------|
| L1 根因 | 模型默认值**跟随运行环境**（不再硬编码 `simulation`）—— 漏传也不会落错 |
| L2 修复 | 补齐所有活代码漏传点（如 `deduct_balance`） |
| L3 守卫 | 写库钩子：生产环境写入 `simulation` 账单 → **ERROR 日志**（让问题发声） |
| L4 可见 | 启动横幅（终端）+ 响应头 `X-Environment` / `X-Billing-Environment` + `/health` 暴露环境 |
| L5 界面 | 前端顶栏**常驻环境徽标** + 生产环境顶部**红色警示条** |

完整说明与回归清单见 [`api-platform/docs/ENVIRONMENT_AND_PAYMENT_MODE.md`](api-platform/docs/ENVIRONMENT_AND_PAYMENT_MODE.md)；
环境变量模板见 [`api-platform/.env.example`](api-platform/.env.example)。

### 13.7 安全加固（SSRF / 凭据 / 权限）

| 项目 | 措施 |
|------|------|
| **仓库转发 SSRF 防护** | 仅允许 `http/https`；**云元数据地址始终拦截**；私网/环回默认"非生产允许、生产禁止"（`ALLOW_PRIVATE_REPO_ENDPOINTS`）；域名 DNS 逐 IP 校验；解析失败 fail-closed |
| **凭据治理** | `keys/`、`*.pem`、`*.key`、`.env.*`、`*.db` 已加入 `.gitignore`；历史误提交的支付宝私钥已 `git rm --cached` 移出索引（⚠️ 需人工轮换密钥） |
| **权限校验统一** | 管理员校验唯一入口 `auth_service.check_admin_permission()`（委托 `PermissionService`），已清除各模块本地副本 |
| **路由注册去重** | 路由统一在 `api/v1/__init__.py` 注册；消除 `/api/v1/files` 等无前缀暴露路径 |

完整说明见 [`api-platform/docs/SECURITY_HARDENING.md`](api-platform/docs/SECURITY_HARDENING.md)。

---

## 十四、部署

### 14.1 Docker Compose（推荐）

`api-platform/docker/docker-compose.yml` 已编排完整服务：

| 服务 | 端口 | 说明 |
|------|------|------|
| postgres | 5432 | PostgreSQL 15 |
| redis | 6379 | Redis 7 |
| minio | 9000 / 9001 | 对象存储 |
| backend | 8000 | FastAPI 后端 |
| frontend | 80 | Nginx 托管前端静态资源 |
| nginx | 8080 / 8443 | 反向代理（profile: `with-nginx`） |
| prometheus / grafana | 9090 / 3001 | 监控（profile: `with-monitoring`） |

```bash
cd api-platform/docker
docker-compose up -d                      # 基础服务
docker-compose --profile with-nginx up -d # 含 Nginx
docker-compose --profile with-monitoring up -d   # 含监控
```

### 14.2 Makefile 常用命令

```bash
make install     # 安装依赖
make dev         # 安装开发依赖
make test        # 运行测试
make test-cov    # 覆盖率测试
make lint        # flake8 + mypy + pylint
make format      # black + isort
make docker-up   # 启动 Docker 服务
make db-init     # 初始化数据库
make db-seed     # 灌入测试数据
make db-reset    # 重置数据库
make run         # 启动开发服务器
```

### 14.3 Electron 桌面端

```bash
cd electron
npm install
npm start        # 开发运行（需本地 Docker）
npm run dist:win # 打包 Windows 安装包（dist/）
npm run dist:mac # macOS
npm run dist:linux # Linux
```

---

## 十五、测试

### 15.1 后端测试

```bash
cd api-platform
pytest                                   # 全部测试（当前 230 passed）
pytest --cov=src --cov-report=html       # 覆盖率报告
pytest tests/test_environment_guard.py -v  # 环境隔离与支付门控专项
```

测试目录 `api-platform/tests/`；工程内还包含大量 `scripts/test_*.py` 集成验证脚本。

> **⚠️ 前置条件**：PostgreSQL 已启动，且已创建**专用测试库** `api_platform_test`
> （测试会在每个用例后 DROP 所有表，**绝不能指向开发库**；`conftest.py` 已加安全护栏，
> 库名不含 `test` 时拒绝运行）：
>
> ```powershell
> $env:PGPASSWORD='postgres'
> & "D:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U postgres -d postgres `
>     -c "CREATE DATABASE api_platform_test OWNER api_user;"
> ```
> 历史问题：`tests/__init__.py` 曾误写入应用导入导致 pytest 收集 0 条用例，已于 2026-09-15 修复（详见 `api-platform/docs/ENVIRONMENT_AND_PAYMENT_MODE.md` 附录）。
> 分层用例：环境/支付门控 22 条、SSRF/权限/路由 39 条、限流 18 条、脱敏 41 条、缓存 12 条。

### 15.2 前端类型检查与静态检查

```bash
cd api-platform/web
npm run typecheck    # 类型检查（tsc --noEmit，当前 0 错误）
npm run build        # 生产构建（tsc && vite build）
npm run lint         # ESLint
```

> **提交前防线（已自动生效）**：仓库内 `.githooks/pre-commit` 会在提交涉及
> `web/src/**/*.ts(x)` 变更时**自动执行类型检查**，不通过则拒绝提交
> （临时跳过用 `git commit --no-verify`）。
> 新环境 / 换机器首次使用请运行 `api-platform/scripts/dev/setup_git_hooks.bat`
> （等价于 `git config core.hooksPath .githooks`）。
>
> **为什么必须做**：`tsc` 一旦发现**语法错误**就会跳过**全部语义（类型）检查** ——
> 曾因 1 个 `.ts` 文件里误写 JSX，导致 **48 个类型错误长期隐身**
> （详见 `api-platform/docs/OPTIMIZATION_BACKLOG.md` §2.10）。

### 15.3 前端 E2E 测试（Playwright）

```bash
cd api-platform/web
npm run test:e2e           # 运行 E2E
npm run test:e2e:ui        # UI 模式
npm run test:e2e:report    # 查看报告
```

### 15.4 测试文档

`api-platform/docs/`：`TEST_PLAN.md`、`TEST_REPORT.md`、`Test_ALL_PLAN.md`、`TEST_SETUP.md`、`WINDOWS_TEST_ENVIRONMENT.md` 等。

---

## 十六、开发规范

### 16.1 代码规范

```bash
# 后端
black src/ tests/        # 格式化
isort src/ tests/        # import 排序
flake8 src/ tests/       # 风格检查
mypy src/                # 类型检查
pylint src/              # 静态分析

# 前端
cd web && npm run lint   # ESLint
cd web && npm run format # Prettier
```

### 16.2 Git 提交规范

```
feat(api): add new API endpoint
fix(auth): resolve authentication issue
docs: update documentation
refactor: restructure code
test: add unit tests
```

### 16.3 约定

- 时间统一使用 **UTC**（`datetime.now(timezone.utc)` / `get_utc_now()`），前端负责本地化展示
- 金额统一使用 `Decimal` / `Numeric`
- 事务由调用方统一 `commit`，Service 层只 `flush`
- 统一走 `PermissionService` 做权限判断
- 统一响应结构与错误码规范

---

## 十七、外网穿透配置

本地开发需将服务暴露到公网以测试支付回调等，项目采用 **ngrok（后端）+ Cloudflare Tunnel（前端）** 双隧道方案。

```bash
# 1. 启动后端
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 2. 启动前端
cd web && npm run dev

# 3. ngrok 暴露后端（固定 URL）
ngrok start --config=ngrok.yml backend     # https://xxxx.ngrok-free.dev -> :8000

# 4. cloudflared 暴露前端（每次重启 URL 变化！）
cloudflared tunnel --url http://localhost:3000 --protocol http2

# 5. 更新 .env 中的 FRONTEND_BASE_URL 为新的 Cloudflare URL
FRONTEND_BASE_URL=https://xxxxxxxx.trycloudflare.com
ALIPAY_NOTIFY_URL=https://xxxxxxxx.ngrok-free.dev/api/v1/payments/alipay/callback
ALIPAY_RETURN_URL=https://xxxxxxxx.ngrok-free.dev/api/v1/payments/alipay/return

# 6. 重启后端加载新环境变量
```

> 详见 `api-platform/README.md` 与外网穿透章节。

---

## 十八、文档索引

项目文档分两套：

### 18.1 平台级文档 `Doc/`（40+ 篇）

| 类别 | 代表文档 |
|------|----------|
| 项目管理 | `01_项目需求规格说明书` `02_项目实施方案` `03_开发周期计划` `04_SOW` `05_验收测试报告` `06_SWOT` `07_改进建议` |
| 技术设计 | `08_数据库设计文档` `09_接口设计文档` `18_通用API服务平台架构` `19_UI设计文档_竹韵赛博风` |
| 运维安全 | `10_部署运维手册` `11_安全设计文档` `14_全自动安装部署指南` `15_开发环境搭建指南` |
| 客户端/集成 | `16_客户端技术方案` `17_第三方API访问方案` |
| 开发 FAQ | `33~41_开发过程中的FAQ_更新*.md`（累计 150+ 问题） |
| 专项 | `支付对账系统设计方案` `支付渠道配置指南` `38_仓库发布与审核流程设计文档` |

- 文档总索引：`Doc/00_文档索引.md`

### 18.2 对外发布文档 `通用API服务平台文档/`

含 `md` + `docx` 双版本：需求规格、实施方案、开发周期、SOW、验收测试、风险分析、改进建议、数据库/接口设计、图例规范、新人上手指南、快速开始教程、SDK 使用手册、故障排查手册、环境配置 FAQ。

### 18.3 工程级文档 `api-platform/docs/`

`ROLE_PERMISSION_GUIDE.md`、`DEVELOPMENT_GUIDE.md`、`LOGGING_GUIDE.md`、支付流程与问题记录、`TEST_*.md`、`WINDOWS_*_ENVIRONMENT.md`、`BUG_FIXES.md`。

> 📖 **全部文档的统一入口**：[`文档导航.md`](./文档导航.md)
> —— 树形 + 表格索引，含全项目每个 `.md` 文档的**名称、路径与内容说明**，以及按角色/目的的阅读路径。

**治理专题文档**：

| 文档 | 内容 |
|------|------|
| `ENVIRONMENT_AND_PAYMENT_MODE.md` | 环境分层、生产强校验、账单环境隔离、支付回调门控；附录含测试环境修复记录 |
| `SECURITY_HARDENING.md` | 凭据治理、SSRF 防护、权限统一、路由去重 |
| `OPTIMIZATION_BACKLOG.md` | **优化跟踪与待办清单**（全部评审项状态、方案、验收标准、人工待办） |

---

## 十九、常见问题（FAQ）

| 问题 | 处理 |
|------|------|
| 前端 404 / 数据加载失败 | 确认后端已启动、路由前缀 `/api/v1`、Token 有效 |
| Windows 下 uvicorn 日志异常 | 项目已主动禁用 uvicorn/sqlalchemy 控制台日志，属正常适配 |
| 支付宝沙箱回调失败 | 检查隧道 URL 是否为最新、`ALIPAY_NOTIFY_URL` 是否已更新并重启后端 |
| 时间显示偏差 | 后端 UTC、前端本地化；确认 `SET TIME ZONE 'UTC'` 生效 |
| 并发下账户重复创建 | `accounts` 表已加唯一约束 `(user_id, account_type)`，代码捕获 `IntegrityError` |

更完整的 FAQ 见 `Doc/13_FAQ常见问题.md`、`Doc/33~41_开发过程中的FAQ_更新*.md`。

---

## 二十、许可证

MIT License

---

**文档版本**：V1.0（基于当前代码库整理）
**整理日期**：2026-09-15
**维护**：项目团队 / AI Assistant
