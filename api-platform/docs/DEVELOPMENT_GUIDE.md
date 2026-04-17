# Windows 开发环境指南

## 环境说明

本项目包含**后端 API 服务**和**前端 Web 控制台**两个部分。

---

## 一、后端环境

### 1.1 快速启动

```powershell
# 1. 进入后端目录
cd d:\Work_Area\AI\API-Agent\api-platform

# 2. 设置环境变量 (PowerShell)
$env:ENVIRONMENT = "test"
$env:DATABASE_URL = "postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform"

# 3. 初始化数据库 (首次运行)
python scripts/init_db_with_data.py --drop

# 4. 启动后端服务
python -m uvicorn src.main:app --reload --port 8080
```

### 1.2 测试数据说明

运行 `init_db_with_data.py` 后，会创建以下测试数据：

| 表名 | 数量 | 说明 |
|------|------|------|
| users | 4 | 管理员、仓库所有者、开发者、测试用户 |
| accounts | 4 | 每个用户对应一个账户 |
| api_keys | 3 | API 密钥 |
| repositories | 3 | API 仓库 |
| bills | 3 | 账单记录 |
| key_usage_logs | 3 | 调用日志 |
| quotas | 3 | 配额记录 |

### 1.3 测试账户

| 用户类型 | 邮箱 | 密码 | VIP等级 |
|----------|------|------|---------|
| Admin | admin@example.com | admin123 | 3 |
| Owner | owner@example.com | owner123 | 2 |
| Developer | developer@example.com | dev123456 | 1 |
| Test | test@example.com | test123 | 0 |

### 1.4 数据库管理命令

```powershell
# 初始化空数据库
python scripts/init_db.py

# 初始化数据库 + 测试数据
python scripts/init_db_with_data.py --drop

# 查看数据库表
python -m scripts.check_tables

# 仅重建数据库
python scripts/init_db_with_data.py --drop --no-sample-data
```

---

## 二、前端环境

### 2.1 快速启动

```powershell
# 1. 进入前端目录
cd d:\Work_Area\AI\API-Agent\api-platform\web

# 2. 安装依赖 (首次运行)
npm install

# 3. 启动开发服务器
npm run dev
```

### 2.2 前端构建

```powershell
# 构建生产版本
npm run build

# 预览构建结果
npm run preview
```

### 2.3 E2E 测试

```powershell
# 安装 Playwright (首次)
npx playwright install chromium

# 运行 E2E 测试
npm run test:e2e

# UI 模式运行
npm run test:e2e:ui
```

---

## 三、访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost:3000 | Web 控制台 |
| 后端 API | http://localhost:8080 | REST API |
| API 文档 | http://localhost:8080/docs | Swagger 文档 |

---

## 四、测试运行

### 4.1 后端测试

```powershell
cd d:\Work_Area\AI\API-Agent\api-platform

# 运行所有测试
python -m pytest tests/ -v

# 运行指定模块
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_billing.py -v
python -m pytest tests/test_repositories.py -v

# 简洁输出
python -m pytest tests/ --tb=no -q
```

### 4.2 测试结果

| 模块 | 测试数 | 状态 |
|------|--------|------|
| test_auth.py | 12 | 全部通过 |
| test_billing.py | 11 | 全部通过 |
| test_repositories.py | 5 | 全部通过 |
| **总计** | **28** | **全部通过** |

---

## 五、数据库配置

### 5.1 连接信息

```
数据库: PostgreSQL
地址: localhost:5432
数据库名: api_platform
用户名: api_user
密码: api_password
```

### 5.2 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| ENVIRONMENT | 环境标识 | test / production |
| DATABASE_URL | 数据库连接 | postgresql+asyncpg://... |

### 5.3 测试/生产环境区分

在 `.env` 文件中设置不同配置：

```env
# 测试环境
ENVIRONMENT=test
DATABASE_URL=postgresql+asyncpg://api_user:api_password@localhost:5432/api_platform_test

# 生产环境
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://user:password@production-host:5432/api_platform
```

---

## 六、常见问题

### Q1: 数据库连接失败

确保 PostgreSQL 服务已启动：

```powershell
# Windows 服务检查
Get-Service -Name postgresql*
```

### Q2: npm install 失败

清除缓存重试：

```powershell
npm cache clean --force
rm -rf node_modules
npm install
```

### Q3: 前端构建报错

检查 TypeScript 配置：

```powershell
npx tsc --noEmit
```

---

## 七、SQL 脚本

### 7.1 脚本位置

```
scripts/sql/
├── init_test_data.sql    # 初始化测试数据
└── clean_test_data.sql   # 清空测试数据
```

### 7.2 使用方法

```powershell
# 初始化测试数据
psql -U api_user -d api_platform -f scripts/sql/init_test_data.sql

# 清空测试数据
psql -U api_user -d api_platform -f scripts/sql/clean_test_data.sql
```

### 7.3 Python 脚本方式

```powershell
# 初始化数据库 + 测试数据
python scripts/init_db_with_data.py --drop

# 仅清空数据
psql -U api_user -d api_platform -f scripts/sql/clean_test_data.sql
```

---

## 八、日志系统

### 8.1 日志配置

在 `.env` 文件中配置：

```env
# 日志级别
LOG_LEVEL=DEBUG           # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE=logs/api_platform.log
LOG_ENABLE_CONSOLE=true   # 控制台输出
LOG_ENABLE_FILE=true      # 文件输出

# 自动备份配置
LOG_BACKUP_MAX_SIZE_MB=10      # 单文件最大大小
LOG_BACKUP_MAX_FILES=100       # 最大备份数量
LOG_BACKUP_AUTO_CLEANUP=true   # 自动清理
LOG_BACKUP_ENABLED=true        # 启用备份
```

### 8.2 日志级别

| 级别 | 说明 | Web颜色 |
|------|------|--------|
| DEBUG | 所有日志 (开发) | 蓝色 |
| INFO | 一般信息 (测试) | 绿色 |
| WARNING | 警告信息 | 橙色 |
| ERROR | 错误信息 | 红色 |
| CRITICAL | 严重错误 | 紫色 |

### 8.3 日志文件位置

```
logs/
├── api_platform.log              # 主日志
├── backup_config.json            # 备份配置
├── modules/                      # 模块日志
│   ├── auth.log
│   ├── billing.log
│   └── middleware.log
└── backups/                      # 备份目录
    └── {module}_{timestamp}.log
```

### 8.4 Web管理

管理员登录后访问 `/admin/logs` 可查看和管理日志：

- **统计概览** - 文件数量、大小统计
- **日志查看** - 分页、级别过滤、关键词搜索
- **备份管理** - 查看、下载、删除备份
- **配置管理** - 调整备份参数

详细说明见 [日志指南](./LOGGING_GUIDE.md)

---

## 九、安全配置

### 9.1 密码哈希配置

系统支持多种密码哈希算法，可在 `.env` 中配置：

```env
# 密码哈希模式: bcrypt (推荐), sha256 (快速), auto (兼容两种)
PASSWORD_HASH_MODE=auto
```

| 模式 | 说明 | 安全性 | 性能 |
|------|------|--------|------|
| bcrypt | 推荐使用 | 高 | 中 |
| sha256 | 兼容旧数据 | 中 | 快 |
| auto | 自动识别现有格式 | 高 | 中 |

### 9.2 兼容性说明

- **向后兼容**: `verify_password()` 函数同时支持 bcrypt 和 SHA256 格式
- **自动升级**: 建议用户首次登录后重置密码以升级到更安全的格式
- **迁移策略**: 逐步将数据库中的 SHA256 哈希迁移到 bcrypt

### 9.3 前端错误处理

前端 API 客户端已优化错误提示：

```typescript
// 401 错误会显示具体消息
// 403 无权限访问
// 404 资源不存在
// 429 请求过于频繁
// 500 服务器错误
```

### 9.4 前端日志系统

前端内置日志系统，方便调试和问题排查：

```typescript
// 日志访问路径
// 管理员登录后访问 /admin/devtools 查看日志
```

日志功能：
- 支持 DEBUG / INFO / WARN / ERROR 四个级别
- 日志自动保存到 localStorage
- 支持导出日志文件
- 支持清空日志

### 9.5 测试账号

| 用户类型 | 邮箱 | 密码 | VIP等级 |
|----------|------|------|---------|
