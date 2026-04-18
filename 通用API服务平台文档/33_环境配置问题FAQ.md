# 通用API服务平台 - 环境配置问题FAQ

## 文档控制

| 项目 | 内容 |
|------|------|
| 文档编号 | FAQ-ENV-2026-001 |
| 版本号 | V1.1 |
| 创建日期 | 2026-04-18 |
| 更新日期 | 2026-04-18 |

---

## 目录

1. [文档说明](#文档说明)
2. [Docker Desktop 镜像拉取问题](#q1-docker-desktop-镜像拉取失败)
3. [使用本机 PostgreSQL 和 Redis](#q2-使用本机-postgresql-和-redis-替代-docker)
4. [Windows print() 兼容性问题](#q3-windows-异步环境-print-兼容性问题)
5. [Windows 安装 Redis](#q4-windows-安装-redis)
6. [数据库初始化常见问题](#q5-数据库初始化常见问题)
7. [API 服务启动和访问](#q6-api-服务启动后无法访问)
8. [PowerShell 环境变量配置](#q7-windows-powershell-环境变量配置)
9. [快速故障排查流程](#快速故障排查流程)
10. [测试账号和接口](#附录a-测试账号和接口)

---

## 文档说明

本FAQ文档记录了通用API服务平台在Windows环境下配置和部署过程中遇到的常见问题及其解决方案。所有问题均基于实际配置经验整理，适用于使用Docker Desktop、PostgreSQL、Redis和FastAPI的开发者和运维人员。

---

## Q1: Docker Desktop 镜像拉取失败

### 问题描述

执行 `docker pull` 命令时，出现以下错误：

```
Error response from daemon: unable to fetch descriptor (sha256:xxx) 
which reports content size of zero: invalid argument
```

或者：

```
docker pull https://docker.1ms.run/library/redis
invalid reference format
```

### 原因分析

1. **Docker Hub 注册表连接异常**：官方镜像仓库连接不稳定
2. **镜像缓存损坏**：之前下载的部分数据损坏
3. **网络问题**：下载过程中网络中断
4. **镜像加速器配置不当**：配置的加速器地址无效

### 解决方案

#### 方案一：配置 Docker 镜像加速器（推荐）

1. 打开 Docker Desktop
2. 点击右上角 **设置（Settings）** → **Docker Engine**
3. 在编辑器中添加镜像源配置：

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "registry-mirrors": [
    "https://docker.xuanyuan.me",
    "https://hub-mirror.c.163.com",
    "https://mirror.ccs.tencentyun.com",
    "https://hub.rat.dev",
    "https://docker.1ms.run",
    "https://pull.m.daocloud.io"
  ]
}
```

4. 点击 **Apply & Restart** 等待 Docker 重启完成

#### 方案二：清理缓存后重试

```powershell
# 清理所有未使用的资源
docker system prune -a -f --volumes

# 重启 Docker Desktop
# 然后重新拉取镜像
docker pull redis:7-alpine
docker pull postgres:15-alpine
```

#### 方案三：完全重启 Docker Desktop

1. 关闭 Docker Desktop（右键托盘图标 → Quit Docker Desktop）
2. 等待完全退出（约30秒）
3. 重新启动 Docker Desktop
4. 等待 Docker 完全启动（托盘图标稳定）
5. 再次尝试拉取镜像

#### 方案四：使用本机服务替代 Docker

如果镜像拉取问题持续，可以直接使用本机已安装的 PostgreSQL 和 Redis（详见 Q2）。

---

## Q2: 使用本机 PostgreSQL 和 Redis 替代 Docker

### 适用场景

- Docker Desktop 镜像拉取困难
- 本机已安装 PostgreSQL 和 Redis
- 需要快速启动开发环境

### 操作步骤

#### 1. 检查本机服务状态

```powershell
# 检查 PostgreSQL（默认端口 5432）
netstat -an | Select-String "5432"

# 检查 Redis（默认端口 6379）
netstat -an | Select-String "6379"
```

#### 2. 配置 .env 文件

打开 `api-platform/config/.env` 文件，修改数据库连接配置：

```env
# PostgreSQL 配置
# 格式: postgresql://用户名:密码@主机:端口/数据库名
DATABASE_URL=postgresql://postgres:superuser@localhost:5432/api_platform

# Redis 配置（无密码）
REDIS_URL=redis://localhost:6379/0
```

#### 3. 创建数据库（如不存在）

```powershell
# 使用 pgAdmin 或 psql 创建数据库
psql -U postgres -c "CREATE DATABASE api_platform;"
```

#### 4. 初始化数据库

```powershell
cd D:\Work_Area\AI\API-Agent\api-platform

# 创建数据库表结构
python scripts/init_db.py

# 填充测试数据
python scripts/seed_data.py
```

#### 5. 启动 API 服务

```powershell
# 进入项目目录
cd D:\Work_Area\AI\API-Agent\api-platform

# 启动服务
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

### 验证服务

```powershell
# 检查健康状态
curl http://localhost:8080/health

# 访问 API 文档
# 浏览器打开: http://localhost:8080/docs
```

---

## Q3: Windows 异步环境 print()/logging 兼容性问题

### 问题描述

在 Windows 上运行 FastAPI 应用时，登录接口报错：

```
OSError: [Errno 22] Invalid argument
```

错误堆栈：

```
File "auth.py", line 164, in login
    print(f"[DEBUG LOGIN] Attempt for: {login_value}")
OSError: [Errno 22] Invalid argument
```

或者即使使用 `logging` 模块仍然报错：

```
File "D:\Work_Area\AI\API-Agent\api-platform\src\api\v1\auth.py", line 164, in login
OSError: [Errno 22] Invalid argument
```

### 原因分析

在 Windows 平台上，`print()` 和 `logging.StreamHandler(sys.stdout)` 在异步环境（asyncio/Starlette）中写入标准输出时可能触发此错误。这通常发生在：

1. 标准输出被重定向或管道传输时
2. 异步任务中直接调用 print()/logging
3. StreamHandler 初始化时的问题

### 解决方案

#### 方案一：移除调试日志（推荐）

最简单有效的方案是完全移除业务代码中的调试日志：

```python
# 移除所有调试日志调用
# 原代码：
# _logger = logging.getLogger("api_platform.auth")
# _logger.debug(f"Login attempt for: {login_value}")

# 直接使用简洁的业务逻辑
login_value = login_data.email
if "@" in login_value:
    result = await db.execute(select(User).where(User.email == login_value))
```

#### 方案二：修复日志配置

如果需要保留日志功能，修改 `src/config/logging_config.py` 中的 StreamHandler：

```python
# 控制台处理器 - 添加 Windows 兼容处理
if enable_console:
    try:
        if sys.platform == 'win32':
            # Windows 异步环境兼容：使用 stdout.buffer
            console_handler = logging.StreamHandler(
                sys.stdout.buffer if hasattr(sys.stdout, 'buffer') else open(os.devnull, 'w')
            )
        else:
            console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(LogConfig.LEVELS.get(level.upper(), logging.INFO))
        console_handler.setFormatter(colored_formatter)
        logger.addHandler(console_handler)
    except Exception:
        pass  # 静默忽略日志初始化错误
```

#### 方案三：清理 Python 缓存并重启

修改代码后，必须清理缓存并**完全重启**服务器：

```powershell
# 1. 强制停止所有 Python 进程
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# 2. 清理所有 __pycache__ 目录
cd D:\Work_Area\AI\API-Agent\api-platform
Get-ChildItem -Path . -Recurse -Include "__pycache__" -Directory | Remove-Item -Recurse -Force

# 3. 清理 .pyc 文件
Get-ChildItem -Path . -Recurse -Filter "*.pyc" | Remove-Item -Force

# 4. 重新启动服务
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

### 注意事项

1. **uvicorn --reload 可能不生效**：在 Windows 上，即使使用 `--reload`，某些情况下旧代码仍然会被使用。**强烈建议手动重启服务**。

2. **日志文件位置**：错误信息会记录到日志文件：
   - 主日志：`api-platform/logs/server_api_platform_YYYYMMDD.log`
   - 模块日志：`api-platform/logs/modules/middleware.log`

3. **调试建议**：如果问题仍然存在，检查日志文件确认服务器是否加载了新代码。

### 完整的修复清单

| 文件 | 修改内容 |
|------|----------|
| `src/api/v1/auth.py` | 移除所有调试日志调用 |
| `src/config/logging_config.py` | StreamHandler 添加 try-except 和 Windows 兼容处理 |
| `__pycache__` | 清理所有缓存目录 |
| 服务器进程 | 完全重启 |

---

## Q4: Windows 安装 Redis

### 推荐方案

#### 方法一：使用 Memurai（推荐）

Memurai 是 Windows 原生的 Redis 替代品，完全兼容 Redis 协议。

1. **下载地址**：https://www.memurai.com/get-download
2. **安装**：运行安装程序，按提示完成安装
3. **自动启动**：安装后自动注册为 Windows 服务并启动
4. **默认配置**：
   - 端口：6379
   - 无密码

#### 方法二：使用 Docker（需要 Docker Desktop 正常运行）

```powershell
docker pull redis:7-alpine
docker run -d --name my-redis -p 6379:6379 redis:7-alpine
```

#### 方法三：使用 WSL2

```bash
# 在 WSL2 终端中
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

### 验证安装

```powershell
# 方法1：检查端口
netstat -an | Select-String "6379"

# 方法2：使用 redis-cli（如已安装）
redis-cli ping
# 应返回: PONG

# 方法3：使用 PowerShell 测试
powershell -c "New-Object System.Net.Sockets.TcpClient('localhost', 6379)"
```

---

## Q5: 数据库初始化常见问题

### 问题1：connection refused

**错误信息**：
```
connection refused
Is the server running on host "localhost" and accepting
TCP/IP connections on port 5432?
```

**原因**：PostgreSQL 服务未启动

**解决方案**：
```powershell
# Windows 服务方式启动
Start-Service postgresql*

# 或使用 pg_ctl
pg_ctl start -D "C:\Program Files\PostgreSQL\15\data"
```

### 问题2：password authentication failed

**错误信息**：
```
password authentication failed for user "postgres"
```

**原因**：密码不正确

**解决方案**：
1. 确认 .env 文件中的密码
2. 本项目配置的密码为：`superuser`

```env
DATABASE_URL=postgresql://postgres:superuser@localhost:5432/api_platform
```

### 问题3：database "xxx" does not exist

**错误信息**：
```
database "api_platform" does not exist
```

**解决方案**：
```powershell
# 创建数据库
psql -U postgres -c "CREATE DATABASE api_platform;"

# 或使用 createdb
createdb -U postgres api_platform
```

### 问题4：permission denied

**错误信息**：
```
permission denied for database "postgres"
```

**解决方案**：
使用 postgres 超级用户连接，或授权：

```powershell
psql -U postgres
# 在 psql 中执行
GRANT ALL PRIVILEGES ON DATABASE api_platform TO postgres;
```

### 完全重置数据库

```powershell
cd D:\Work_Area\AI\API-Agent\api-platform

# 删除并重建表
python scripts/init_db.py --drop

# 重新初始化
python scripts/init_db.py

# 填充测试数据
python scripts/seed_data.py
```

---

## Q6: API 服务启动后无法访问

### 问题描述

API 服务已启动，但无法访问 http://localhost:8080

### 排查步骤

#### 步骤1：确认服务正在运行

```powershell
# 检查端口监听
netstat -an | Select-String "8080"

# 应该看到类似输出：
# TCP    0.0.0.0:8080    0.0.0.0:0    LISTENING
```

#### 步骤2：检查防火墙

```powershell
# 临时关闭防火墙测试
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False

# 或添加规则
netsh advfirewall firewall add rule name="API Platform" dir=in action=allow protocol=tcp localport=8080
```

#### 步骤3：查看启动日志

```powershell
cd D:\Work_Area\AI\API-Agent\api-platform
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

观察是否有错误信息。

#### 步骤4：验证 .env 配置

确认 `config/.env` 文件中：

```env
DATABASE_URL=postgresql://postgres:superuser@localhost:5432/api_platform
REDIS_URL=redis://localhost:6379/0
DEBUG=true
```

#### 步骤5：测试数据库连接

```powershell
cd D:\Work_Area\AI\API-Agent\api-platform
python -c "from src.config.database import async_engine; import asyncio; asyncio.run(async_engine.connect().__aenter__()); print('DB OK')"
```

### 常见错误及解决方案

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| `ModuleNotFoundError` | 依赖未安装 | `pip install -r requirements.txt` |
| `Connection refused` | 数据库未启动 | 启动 PostgreSQL |
| `Connection refused` | Redis 未启动 | 启动 Redis |
| `Address already in use` | 端口被占用 | 更换端口或结束占用进程 |

---

## Q7: Windows PowerShell 环境变量配置

### 临时设置（当前会话）

```powershell
# 设置环境变量
$env:DATABASE_URL = "postgresql://postgres:superuser@localhost:5432/api_platform"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:DEBUG = "true"

# 查看所有环境变量
Get-ChildItem Env:

# 查看特定变量
$env:DATABASE_URL
```

### 永久设置（用户级）

```powershell
# 永久设置（用户级）
[System.Environment]::SetEnvironmentVariable("DATABASE_URL", "postgresql://postgres:superuser@localhost:5432/api_platform", "User")

# 永久设置（系统级，需要管理员权限）
[System.Environment]::SetEnvironmentVariable("DATABASE_URL", "postgresql://postgres:superuser@localhost:5432/api_platform", "Machine")
```

### 使用 .env 文件（推荐）

项目根目录的 `.env` 文件会被自动加载，无需手动设置环境变量。

确保 `.env` 文件存在且配置正确：

```env
# api-platform/config/.env
DATABASE_URL=postgresql://postgres:superuser@localhost:5432/api_platform
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
DEBUG=true
```

---

## 快速故障排查流程

当遇到问题时，请按以下顺序排查：

```
1. Docker Desktop 是否运行？
   ├─ 是 → 继续
   └─ 否 → 启动 Docker Desktop

2. PostgreSQL 是否运行？
   ├─ 是 → 继续
   └─ 否 → 启动 PostgreSQL 服务

3. Redis 是否运行？
   ├─ 是 → 继续
   └─ 否 → 启动 Redis/Memurai

4. .env 配置是否正确？
   ├─ 是 → 继续
   └─ 否 → 修正配置

5. 数据库是否已初始化？
   ├─ 是 → 继续
   └─ 否 → 运行 init_db.py 和 seed_data.py

6. API 服务是否正常启动？
   ├─ 是 → 完成
   └─ 否 → 查看错误日志并对照本文档解决
```

---

## 附录A: 测试账号和接口

### 测试账号

| 角色 | 邮箱 | 密码 | 说明 |
|------|------|------|------|
| 管理员 | admin@example.com | admin123 | 管理员账号，拥有全部权限 |
| 开发者 | developer@example.com | dev123456 | 开发者账号 |
| 仓库所有者 | owner@example.com | owner123456 | 仓库所有者账号 |

### 常用 API 接口

```bash
# 健康检查
GET http://localhost:8080/health

# 登录
POST http://localhost:8080/api/v1/auth/login
Content-Type: application/json
{
  "email": "admin@example.com",
  "password": "admin123"
}

# API 文档
# http://localhost:8080/docs (Swagger UI)
# http://localhost:8080/redoc (ReDoc)
```

### 常用命令速查

```powershell
# 启动 API 服务
cd D:\Work_Area\AI\API-Agent\api-platform
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8080

# 初始化数据库
python scripts/init_db.py
python scripts/seed_data.py

# 测试登录
Invoke-RestMethod -Method Post -Uri "http://localhost:8080/api/v1/auth/login" -ContentType "application/json" -Body '{"email":"admin@example.com","password":"admin123"}'
```

---

## 附录B: 相关文档

| 文档名称 | 路径 |
|----------|------|
| 日志配置指南 | `api-platform/docs/LOGGING_GUIDE.md` |
| 端到端测试指南 | `api-platform/web/docs/E2E_TEST_GUIDE.md` |
| 数据库设计文档 | `通用API服务平台文档/26_通用API服务平台数据库设计文档.md` |
| 接口设计文档 | `通用API服务平台文档/27_通用API服务平台接口设计文档.md` |
| 快速开始教程 | `通用API服务平台文档/30_快速开始教程.md` |

---

## 文档版本

| 版本 | 日期 | 更新内容 | 作者 |
|------|------|---------|------|
| V1.0 | 2026-04-18 | 初始版本，记录环境配置问题及解决方案 | AI Assistant |
| V1.1 | 2026-04-18 | 完善 Q3：补充 Windows 异步环境下 logging 兼容性问题的完整解决方案和排查步骤 | AI Assistant |

---

**如有补充或更新建议，请联系项目组。**
