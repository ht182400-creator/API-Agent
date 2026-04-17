# Windows 测试环境完整设置指南

本文档提供在 Windows 系统上设置 API 平台测试环境的完整步骤。

---

## 目录

1. [环境要求](#环境要求)
2. [PostgreSQL 数据库安装与配置](#postgresql-数据库安装与配置)
3. [项目配置](#项目配置)
4. [运行测试](#运行测试)
5. [测试环境与生产环境区分](#测试环境与生产环境区分)
6. [常见问题](#常见问题)

---

## 环境要求

### 软件依赖

| 软件 | 版本要求 | 用途 |
|------|----------|------|
| Python | 3.11+ | 运行环境 |
| PostgreSQL | 14+ | 数据库 |
| Redis | 6+ | 缓存 (可选) |

### 检查 Python 版本

```powershell
python --version
# Python 3.13.3
```

### 安装 Python 依赖

```powershell
cd d:\Work_Area\AI\API-Agent\api-platform
pip install -r requirements.txt
```

---

## PostgreSQL 数据库安装与配置

### 1. 检查 PostgreSQL 服务状态

```powershell
# 检查服务是否运行
Get-Service postgresql*

# 如果未运行，启动服务
Start-Service postgresql-x64-16
```

### 2. 连接 PostgreSQL

```powershell
# 设置密码环境变量
$env:PGPASSWORD = 'postgres'

# 使用 psql 连接
& "D:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U postgres -d postgres
```

### 3. 创建数据库和用户

```powershell
$env:PGPASSWORD = 'postgres'

# 创建数据库
& "D:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U postgres -d postgres -c "CREATE DATABASE api_platform;"

# 创建用户
& "D:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U postgres -d postgres -c "CREATE USER api_user WITH PASSWORD 'api_password';"

# 授予权限
& "D:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U postgres -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE api_platform TO api_user;"

# 授予 Schema 权限
& "D:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U postgres -d api_platform -c "GRANT ALL ON SCHEMA public TO api_user;"

# 授予默认权限
& "D:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U postgres -d api_platform -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO api_user; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO api_user;"
```

### 数据库连接信息

| 参数 | 值 |
|------|-----|
| 主机 | localhost |
| 端口 | 5432 |
| 数据库名 | api_platform |
| 用户名 | api_user |
| 密码 | api_password |
| 连接串 | `postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform` |

---

## 项目配置

### 1. 创建环境配置文件

项目根目录下应该有 `.env` 文件：

```env
# 数据库配置
DATABASE_URL=postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform

# Redis 配置 (可选)
REDIS_URL=redis://localhost:6379/0

# JWT 配置
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440

# 应用配置
APP_NAME=API Platform
APP_VERSION=1.0.0
DEBUG=true

# 测试环境标识
ENVIRONMENT=test
```

### 2. 环境变量说明

| 变量名 | 说明 | 测试环境值 | 生产环境值 |
|--------|------|-----------|-----------|
| `DATABASE_URL` | 数据库连接串 | `postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform` | 使用生产数据库 |
| `ENVIRONMENT` | 环境标识 | `test` | `production` |
| `DEBUG` | 调试模式 | `true` | `false` |
| `REDIS_URL` | Redis 连接 | `redis://localhost:6379/0` | 生产 Redis |

---

## 运行测试

### 运行所有测试

```powershell
cd d:\Work_Area\AI\API-Agent\api-platform
python -m pytest tests/ -v
```

### 运行特定模块测试

```powershell
# 认证测试
python -m pytest tests/test_auth.py -v

# 计费测试
python -m pytest tests/test_billing.py -v

# 仓库测试
python -m pytest tests/test_repositories.py -v
```

### 查看详细输出

```powershell
# 显示 print 输出
python -m pytest tests/ -v -s

# 显示失败详情
python -m pytest tests/ -v --tb=short

# 显示完整失败信息
python -m pytest tests/ -v --tb=long
```

### 测试结果统计

```powershell
# 简洁输出
python -m pytest tests/ --tb=no -q

# 生成覆盖率报告
python -m pytest tests/ --cov=src --cov-report=html
```

---

## 测试环境与生产环境区分

### 方案一：使用 .env 文件区分

项目支持通过 `ENVIRONMENT` 环境变量区分：

```python
# src/config/settings.py 中的配置
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    environment: str = "development"
    
    class Config:
        env_file = ".env"
        
    @property
    def is_test(self) -> bool:
        return self.environment == "test"
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
```

### 方案二：使用独立的测试数据库

```powershell
# 创建测试数据库 (可选，与开发环境隔离)
$env:PGPASSWORD = 'postgres'
& "D:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U postgres -d postgres -c "CREATE DATABASE api_platform_test;"
& "D:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U postgres -d postgres -c "GRANT ALL ON DATABASE api_platform_test TO api_user;"
```

测试时指定测试数据库：

```powershell
# 使用测试数据库运行测试
$env:TEST_DATABASE_URL = "postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform_test"
python -m pytest tests/ -v
```

### 方案三：使用 pytest fixtures 自动切换

在 `tests/conftest.py` 中配置：

```python
import os

# 根据环境变量决定使用哪个数据库
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform"
)

# 设置环境变量
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ENVIRONMENT"] = "test"
```

### 环境对比表

| 特性 | 开发/测试环境 | 生产环境 |
|------|--------------|---------|
| 数据库 | `api_platform` | `api_platform_prod` |
| 用户 | `api_user` | 独立生产用户 |
| 密码 | 简单密码 | 强密码 |
| DEBUG | `true` | `false` |
| 日志级别 | DEBUG | INFO/WARNING |
| 数据清理 | 测试后自动清理 | 不清理 |

### 运行测试时的环境检查

```powershell
# 确保测试环境变量
$env:ENVIRONMENT = "test"
$env:DEBUG = "true"

# 运行测试
python -m pytest tests/ -v --capture=no
```

---

## 常见问题

### 1. psycopg2 编码错误

如果遇到编码错误，设置环境变量：

```powershell
$env:PGCLIENTENCODING = "UTF8"
```

### 2. 连接被拒绝

确保 PostgreSQL 服务正在运行：

```powershell
Start-Service postgresql-x64-16
```

### 3. 密码认证失败

检查 pg_hba.conf 配置：

```powershell
# 临时添加 trust 认证 (仅开发环境!)
# 文件位置: C:\Program Files\PostgreSQL\16\data\pg_hba.conf
# 添加: host all all 127.0.0.1/32 trust

# 重新加载配置
$env:PGPASSWORD = 'postgres'
& "D:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U postgres -d postgres -c "SELECT pg_reload_conf();"
```

### 4. 外键约束错误

确保测试数据库表已正确创建：

```python
# 在 tests/conftest.py 中自动创建
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

### 5. httpx 版本兼容

确保 httpx 版本 >= 0.27.0，使用正确的 AsyncClient 用法：

```python
from httpx import ASGITransport, AsyncClient

async with AsyncClient(
    transport=ASGITransport(app=app),
    base_url="http://test"
) as ac:
    response = await ac.get("/api/v1/...")
```

---

## 快速启动命令汇总

```powershell
# 1. 进入项目目录
cd d:\Work_Area\AI\API-Agent\api-platform

# 2. 设置环境变量
$env:ENVIRONMENT = "test"
$env:PGPASSWORD = 'postgres'

# 3. 运行所有测试
python -m pytest tests/ -v

# 4. 运行特定测试
python -m pytest tests/test_auth.py tests/test_billing.py -v

# 5. 生成覆盖率报告
python -m pytest tests/ --cov=src --cov-report=html
```

---

## 测试结果

运行 `python -m pytest tests/ -v` 应该看到：

```
============================= test session starts =============================
platform win32 -- Python 3.13.3, pytest-9.0.2, pluggy-1.6.0
collected 28 items

tests/test_auth.py::TestPasswordHashing::test_hash_password PASSED       [  3%]
tests/test_auth.py::TestPasswordHashing::test_verify_password_success PASSED [  7%]
tests/test_auth.py::TestPasswordHashing::test_verify_password_failure PASSED [ 10%]
tests/test_auth.py::TestAPIKeyGeneration::test_generate_api_key PASSED   [ 14%]
tests/test_auth.py::TestAPIKeyGeneration::test_hash_api_key PASSED       [ 17%]
tests/test_auth.py::TestJWTToken::test_create_access_token PASSED        [ 21%]
tests/test_auth.py::TestJWTToken::test_verify_token PASSED               [ 25%]
tests/test_auth.py::TestJWTToken::test_verify_invalid_token PASSED       [ 28%]
tests/test_auth.py::TestAuthAPI::test_register PASSED                    [ 32%]
tests/test_auth.py::TestAuthAPI::test_register_duplicate_email PASSED    [ 35%]
tests/test_auth.py::TestAuthAPI::test_login PASSED                       [ 39%]
tests/test_auth.py::TestAuthAPI::test_login_wrong_password PASSED        [ 42%]
tests/test_billing.py::TestBillingService::test_get_account PASSED       [ 46%]
tests/test_billing.py::TestBillingService::test_get_account_auto_create PASSED [ 50%]
tests/test_billing.py::TestBillingService::test_recharge PASSED          [ 53%]
tests/test_billing.py::TestBillingService::test_recharge_negative_amount PASSED [ 57%]
tests/test_billing.py::TestBillingService::test_create_consumption PASSED [ 60%]
tests/test_billing.py::TestBillingService::test_insufficient_balance PASSED [ 64%]
tests/test_billing.py::TestBillingService::test_freeze_balance PASSED    [ 67%]
tests/test_billing.py::TestBillingService::test_unfreeze_balance PASSED   [ 71%]
tests/test_billing.py::TestBillingService::test_refund PASSED            [ 75%]
tests/test_billing.py::TestBillingService::test_get_bills PASSED         [ 78%]
tests/test_billing.py::TestBillingService::test_get_monthly_summary PASSED [100%]
tests/test_repositories.py::TestRepositoryAPI::test_list_repositories PASSED [ 85%]
tests/test_repositories.py::TestRepositoryAPI::test_list_repositories_with_filter PASSED [ 89%]
tests/test_repositories.py::TestRepositoryAPI::test_get_repository_not_found PASSED [ 92%]
tests/test_repositories.py::TestQuotaAPI::test_get_quota PASSED          [ 96%]
tests/test_repositories.py::TestLogsAPI::test_get_logs PASSED            [100%]

============================== 28 passed in 10.37s ==============================
```
