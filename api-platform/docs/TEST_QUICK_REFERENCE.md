# 测试环境快速参考卡

## 数据库连接

| 项目 | 值 |
|------|-----|
| 类型 | PostgreSQL |
| 主机 | localhost |
| 端口 | 5432 |
| 数据库 | api_platform |
| 用户名 | api_user |
| 密码 | api_password |
| 连接串 | `postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform` |

## 常用命令

```powershell
# 运行所有测试
python -m pytest tests/ -v

# 运行认证测试
python -m pytest tests/test_auth.py -v

# 运行测试（详细输出）
python -m pytest tests/ -v --tb=short

# 生成覆盖率报告
python -m pytest tests/ --cov=src --cov-report=html

# 设置数据库密码（如果需要）
$env:PGPASSWORD='postgres'
& "D:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U postgres -d postgres
ALTER USER postgres WITH PASSWORD 'postgres';
```

## 初始化数据库

```powershell
cd api-platform
python scripts/setup_db_simple.py
```

## 环境变量 (.env)

```
DEBUG=true
DATABASE_URL=postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform
SECRET_KEY=dev-secret-key-12345678901234567890
JWT_SECRET_KEY=dev-jwt-secret-key-123456789012345
```

## 测试结果

- ✅ 认证模块: 12/12 通过
- ✅ 仓库模块: 5/5 通过
- ⚠️ 计费模块: 0/6 通过 (需修复测试代码)

**总计**: 17 passed, 6 failed
