# API Platform

通用API服务平台 - API聚合中转站

## 项目简介

通用API服务平台是一个API聚合中转站，通过统一的入口、标准化的认证、智能的路由，将分散的API仓库整合起来，为开发者提供一站式的API服务体验。

## 核心特性

- **统一入口**：一个API Key调用所有仓库
- **统一认证**：API Key + HMAC签名
- **统一计费**：一站式计费和配额管理
- **热插拔**：仓库可动态接入和下线
- **高性能**：10,000 QPS / P99 < 500ms
- **日志管理**：模块分解日志、Web界面查看、自动备份

## 技术栈

- **后端**：Python 3.11+ / FastAPI
- **数据库**：PostgreSQL 15+ / Redis 7+
- **API网关**：APISIX
- **前端**：React + TypeScript
- **部署**：Docker / Kubernetes

## 快速开始

### 环境要求

- Python 3.11+
- Docker Desktop 4.0+
- PostgreSQL 15+
- Redis 7+

### 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
.\venv\Scripts\Activate.ps1  # Windows PowerShell

# 安装依赖
pip install -r requirements.txt
```

### 配置环境变量

```bash
cp config/.env.example config/.env
# 编辑 config/.env 设置数据库连接等信息
```

### 启动服务

```bash
# 启动依赖服务
cd docker
docker-compose up -d postgres redis

# 初始化数据库
python scripts/init_db.py

# 启动API服务
uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

### 访问API文档

- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## 项目结构

```
api-platform/
├── src/                         # 源代码
│   ├── __init__.py
│   ├── main.py                 # 应用入口
│   ├── config/                  # 配置模块
│   │   ├── __init__.py
│   │   ├── settings.py         # 应用设置
│   │   └── database.py         # 数据库配置
│   ├── api/                     # API路由
│   │   ├── __init__.py
│   │   ├── v1/                 # API v1版本
│   │   │   ├── __init__.py
│   │   │   ├── auth.py         # 认证接口
│   │   │   ├── repositories.py # 仓库接口
│   │   │   ├── quota.py        # 配额接口
│   │   │   ├── logs.py         # 日志接口
│   │   │   └── admin_logs.py   # 管理员日志管理接口
│   │   └── __init__.py
│   ├── models/                  # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py             # 用户模型
│   │   ├── api_key.py          # API Key模型
│   │   ├── repository.py        # 仓库模型
│   │   ├── billing.py           # 计费模型
│   │   └── adapter.py           # 适配器模型
│   ├── services/                # 业务逻辑
│   │   ├── __init__.py
│   │   ├── auth_service.py     # 认证服务
│   │   ├── repo_service.py     # 仓库服务
│   │   ├── billing_service.py  # 计费服务
│   │   └── quota_service.py    # 配额服务
│   ├── adapters/                # 适配器
│   │   ├── __init__.py
│   │   ├── base.py             # 适配器基类
│   │   ├── http_adapter.py     # HTTP适配器
│   │   └── grpc_adapter.py     # gRPC适配器
│   ├── schemas/                 # Pydantic模型
│   │   ├── __init__.py
│   │   ├── request.py          # 请求模型
│   │   └── response.py         # 响应模型
│   ├── core/                    # 核心模块
│   │   ├── __init__.py
│   │   ├── security.py         # 安全认证
│   │   ├── exceptions.py       # 异常处理
│   │   └── middleware.py       # 中间件
│   └── utils/                   # 工具函数
│       ├── __init__.py
│       ├── crypto.py           # 加密工具
│       └── helpers.py          # 辅助函数
├── tests/                        # 测试代码
│   ├── __init__.py
│   ├── conftest.py             # pytest配置
│   ├── test_auth.py            # 认证测试
│   ├── test_repositories.py    # 仓库测试
│   └── test_billing.py         # 计费测试
├── docker/                       # Docker配置
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   └── docker-compose.yml
├── scripts/                       # 脚本文件
│   ├── init_db.py              # 数据库初始化
│   └── seed_data.py            # 测试数据
├── config/                       # 配置文件
│   ├── .env.example
│   └── logging.conf
├── docs/                         # 项目文档
│   ├── LOGGING_GUIDE.md          # 日志系统使用指南
│   ├── DEVELOPMENT_GUIDE.md      # 开发指南
│   └── ...
├── logs/                         # 日志目录
│   ├── api_platform.log          # 主日志
│   ├── modules/                  # 模块日志
│   └── backups/                  # 备份目录
├── web/                          # 前端代码
│   └── src/
│       ├── pages/admin/          # 管理员页面
│       │   └── AdminLogs.tsx     # 日志管理页面
│       └── api/
│           └── adminLogs.ts      # 日志API客户端
├── requirements.txt              # Python依赖
├── requirements-dev.txt         # 开发依赖
├── pytest.ini                   # pytest配置
├── pyproject.toml               # 项目配置
├── Makefile                     # Makefile
├── .gitignore
└── README.md
```

## 模块说明

### src/config - 配置模块
- `settings.py`: 应用配置，环境变量管理
- `database.py`: 数据库连接配置
- `logging_config.py`: 日志配置，支持模块分解和自动备份

### src/api - API路由
- `v1/`: API v1版本接口
  - `auth.py`: 认证相关接口
  - `repositories.py`: 仓库调用接口
  - `quota.py`: 配额查询接口
  - `logs.py`: 日志查询接口
  - `admin_logs.py`: 管理员日志管理接口

### src/models - 数据模型
- `user.py`: 用户表模型
- `api_key.py`: API Key表模型
- `repository.py`: 仓库表模型
- `billing.py`: 账单表模型
- `adapter.py`: 适配器表模型

### src/services - 业务逻辑
- `auth_service.py`: 认证服务（API Key验证、HMAC签名）
- `repo_service.py`: 仓库服务（路由分发、请求转发）
- `billing_service.py`: 计费服务（费用计算、扣费）
- `quota_service.py`: 配额服务（限流、配额检查）

### src/adapters - 适配器
- `base.py`: 适配器基类，定义标准接口
- `http_adapter.py`: HTTP适配器实现
- `grpc_adapter.py`: gRPC适配器实现

## API接口

### 开发者API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/v1/repositories` | GET | 获取仓库列表 |
| `/v1/repositories/{slug}` | GET | 获取仓库详情 |
| `/v1/repositories/{slug}/*` | * | 调用仓库API |
| `/v1/quota` | GET | 查询配额 |
| `/v1/logs` | GET | 查询调用日志 |

### 管理API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/v1/admin/users` | GET/POST | 用户管理 |
| `/v1/admin/keys` | GET/POST | Key管理 |
| `/v1/admin/repositories` | GET/POST | 仓库管理 |
| `/v1/admin/stats` | GET | 统计数据 |
| `/v1/admin/logs/files` | GET | 获取日志文件列表 |
| `/v1/admin/logs/content` | GET | 获取日志内容 |
| `/v1/admin/logs/stats` | GET | 获取日志统计 |
| `/v1/admin/logs/backups` | GET | 获取备份文件列表 |
| `/v1/admin/logs/config` | GET/PUT | 日志备份配置 |

## 开发指南

### 代码规范

```bash
# 格式化代码
black src/ tests/

# 检查代码风格
flake8 src/ tests/

# 类型检查
mypy src/
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=src --cov-report=html
```

### Git提交规范

```
feat(api): add new API endpoint
fix(auth): resolve authentication issue
docs: update documentation
refactor: restructure code
test: add unit tests
```

## 许可证

MIT License
