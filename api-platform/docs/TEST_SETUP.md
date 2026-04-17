# API Platform 测试指南

## 概述

本文档介绍如何设置和运行 API Platform 项目的测试环境。

## 环境要求

- Python 3.10+
- PostgreSQL 14+
- Redis (可选，用于完整功能测试)

## Windows 环境安装步骤

### 1. 安装 PostgreSQL

如果尚未安装 PostgreSQL：

```powershell
# 使用 Chocolatey 安装
choco install postgresql -y

# 或下载安装包: https://www.postgresql.org/download/windows/
```

### 2. 配置数据库

```powershell
# 连接到 PostgreSQL
$env:PGPASSWORD='postgres'
& "D:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U postgres -d postgres

# 在 psql 中执行:
CREATE DATABASE api_platform;
CREATE USER api_user WITH PASSWORD 'api_password';
GRANT ALL PRIVILEGES ON DATABASE api_platform TO api_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO api_user;
```

或使用提供的脚本：

```powershell
cd api-platform
python scripts/setup_db_simple.py
```

### 3. 安装 Python 依赖

```powershell
# 安装项目依赖
pip install -r requirements.txt

# 安装测试依赖
pip install -r requirements-dev.txt

# 或直接安装测试包
pip install pytest pytest-asyncio pytest-cov httpx asyncpg psycopg2-binary aiosqlite
```

### 4. 配置环境变量

创建 `api-platform/.env` 文件：

```env
# Database
DATABASE_URL=postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform

# Redis (可选)
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key
```

### 5. 运行测试

```powershell
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_auth.py -v

# 运行带详细输出的测试
python -m pytest tests/ -v --tb=short

# 生成覆盖率报告
python -m pytest tests/ --cov=src --cov-report=html
```

## 测试结果

### 当前测试状态

| 测试模块 | 状态 | 说明 |
|---------|------|------|
| test_auth.py | ✅ 12 passed | 认证模块全部通过 |
| test_repositories.py | ✅ 6 passed | 仓库/配额/日志API通过 |
| test_billing.py | ⚠️ 6 failed | 计费服务方法名不匹配 |

### 已知问题

1. **计费测试失败**: 测试代码中使用的方法名与 `BillingService` 实际方法名不匹配
   - 测试期望: `get_or_create_account()`, `calculate_cost()`, `deduct()`
   - 实际方法名需查看 `src/services/billing_service.py`

## 数据库配置

### PostgreSQL 连接参数

```python
{
    'host': 'localhost',
    'port': 5432,
    'user': 'api_user',
    'password': 'api_password',
    'database': 'api_platform'
}
```

### 修改密码（如需要）

```powershell
$env:PGPASSWORD='old_password'
& "D:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U postgres -d postgres
ALTER USER postgres WITH PASSWORD 'new_password';
```

### 常见问题

#### Q: psycopg2 连接报错 "encoding error"
A: 确保数据库配置使用了 UTF8 编码:
```python
conn.set_client_encoding('UTF8')
```

#### Q: 权限错误 "permission denied for schema public"
A: 授予必要权限:
```sql
GRANT ALL PRIVILEGES ON SCHEMA public TO api_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO api_user;
```

## 开发工作流

1. **编写测试**: 在 `tests/` 目录下创建测试文件
2. **运行测试**: `python -m pytest tests/ -v`
3. **调试失败**: 使用 `--tb=short` 查看详细错误
4. **提交代码**: 确保所有测试通过后再提交

## 测试覆盖范围

- ✅ 密码哈希与验证
- ✅ API Key 生成
- ✅ JWT Token 管理
- ✅ 用户注册/登录
- ✅ 仓库列表/过滤
- ✅ 配额查询
- ⚠️ 计费服务 (需要修复测试代码)

## 联系方式

如有问题，请查看项目文档或联系开发团队。
