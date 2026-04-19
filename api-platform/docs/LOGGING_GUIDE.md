# 日志系统使用指南

## 一、特性概述

| 特性 | 说明 |
|------|------|
| 多级别日志 | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| 模块分解 | 按模块输出到独立日志文件 |
| 双输出 | 控制台 + 文件同时记录 |
| 日志轮转 | 按大小(10MB)或时间自动轮转 |
| 彩色输出 | 控制台日志带颜色区分 |
| 自动备份 | 文件超限自动备份到时间戳文件 |
| Web管理 | 管理员界面查看和管理日志 |

---

## 二、日志文件结构

```
logs/
├── server_api_platform_20260418.log              # 主日志 (带日期和前缀)
├── server_api_platform_20260418.log.1            # 轮转备份
├── backup_config.json                              # 备份配置文件
├── modules/                                        # 模块分解日志
│   ├── server_auth_20260418.log                   # 认证模块日志 (带日期和前缀)
│   ├── server_billing_20260418.log                # 计费模块日志
│   ├── server_middleware_20260418.log             # 中间件日志
│   ├── server_repo_20260418.log                  # 仓库模块日志
│   ├── server_quota_20260418.log                 # 配额模块日志
│   ├── server_api_20260418.log                   # API模块日志
│   ├── server_database_20260418.log              # 数据库模块日志
│   └── server_security_20260418.log              # 安全模块日志
└── backups/                                       # 自动备份目录
    ├── api_platform_20260417_234500.log          # 主日志备份
    ├── auth_20260417_234500.log                  # 模块日志备份
    └── ...
```

**文件名格式说明**:

| 端 | 格式 | 示例 |
|---|------|------|
| 后端主日志 | `server_{模块名}_{yyyymmdd}.log` | `server_api_platform_20260418.log` |
| 后端模块日志 | `server_{模块名}_{yyyymmdd}.log` | `server_auth_20260418.log` |
| 后端备份 | `{模块名}_{yyyymmdd_HHmmss}.log` | `api_platform_20260418_194530.log` |
| 前端导出 | `web-app-log_{yyyymmdd-HHmmss}.txt` | `web-app-log-20260418-194530.txt` |
| 前端导出JSON | `web-app-log_{yyyymmdd-HHmmss}.json` | `web-app-log-20260418-194530.json` |

---

## 三、配置说明

### 3.1 环境变量

```env
# 日志级别
LOG_LEVEL=DEBUG              # DEBUG, INFO, WARNING, ERROR, CRITICAL

# 日志文件路径
LOG_FILE=logs/api_platform.log

# 输出控制
LOG_ENABLE_CONSOLE=true      # 控制台输出
LOG_ENABLE_FILE=true         # 文件输出

# 轮转方式
LOG_ROTATION=size           # size: 按大小, time: 按时间

# ===== 自动备份配置 =====
LOG_BACKUP_MAX_SIZE_MB=10      # 单个日志文件最大大小(MB)
LOG_BACKUP_MAX_FILES=100        # 最大备份文件数量
LOG_BACKUP_AUTO_CLEANUP=true    # 是否自动清理旧备份
LOG_BACKUP_CLEANUP_THRESHOLD=80 # 清理阈值(%)
LOG_BACKUP_ENABLED=true         # 是否启用自动备份
```

### 3.2 不同环境推荐配置

| 环境 | LOG_LEVEL | LOG_ENABLE_CONSOLE | 说明 |
|------|-----------|-------------------|------|
| development | DEBUG | true | 详细日志，开发调试 |
| test | INFO | true | 信息日志，测试验证 |
| production | WARNING | false | 警告以上，减少磁盘 |

---

## 四、代码使用

### 4.1 主日志记录器

```python
from src.config.logging_config import logger

logger.debug("调试信息: %s", variable)
logger.info("用户登录: %s", email)
logger.warning("余额不足: %s", user_id)
logger.error("数据库连接失败")
logger.critical("系统无法启动")
```

### 4.2 模块级日志记录器

```python
from src.config.logging_config import get_logger

# 在 src/services/auth_service.py 中
logger = get_logger("auth")
logger.info("认证成功: %s", user_email)

# 在 src/services/billing_service.py 中
logger = get_logger("billing")
logger.info("充值成功: %s, 金额: %s", user_id, amount)
```

### 4.3 快捷函数

```python
from src.config.logging_config import log_info, log_error, log_exception

# 简单使用
log_info("操作成功")
log_error("操作失败")

# 异常记录 (自动包含堆栈)
try:
    risky_operation()
except Exception:
    log_exception("操作失败")
```

### 4.4 异常记录

```python
# 方式1: log_exception (推荐，自动包含堆栈)
try:
    db_operation()
except Exception:
    log.exception("数据库操作失败")

# 方式2: 手动记录
try:
    db_operation()
except Exception as e:
    log.error("数据库操作失败: %s", str(e), exc_info=True)
```

---

## 五、日志级别说明

### 5.1 级别定义

| 级别 | 值 | 颜色 | 使用场景 |
|------|-----|------|----------|
| DEBUG | 10 | 蓝色 #1890ff | 开发调试，变量值 |
| INFO | 20 | 绿色 #52c41a | 正常运行信息 |
| WARNING | 30 | 橙色 #faad14 | 潜在问题 |
| ERROR | 40 | 红色 #ff4d4f | 功能异常 |
| CRITICAL | 50 | 紫色 #722ed1 | 系统故障 |

### 5.2 Web界面级别颜色

在Web管理界面中，不同级别的日志显示不同颜色：

```
[DEBUG]  蓝色背景/左边框 - 调试信息
[INFO]   绿色背景/左边框 - 正常信息
[WARNING]橙色背景/左边框 - 警告信息
[ERROR]  红色背景/左边框 - 错误信息
[CRITICAL]紫色背景/左边框 - 严重错误
```

---

## 六、API接口

### 6.1 日志管理API (仅管理员)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/admin/logs/files | 获取日志文件列表 |
| GET | /api/v1/admin/logs/content | 获取日志内容（支持级别过滤和关键词搜索） |
| GET | /api/v1/admin/logs/export | 导出日志文件（下载完整日志） |
| GET | /api/v1/admin/logs/stats | 获取日志统计 |
| GET | /api/v1/admin/logs/backups | 获取备份文件列表 |
| GET | /api/v1/admin/logs/backup-content | 查看备份文件内容（支持级别过滤和关键词搜索） |
| GET | /api/v1/admin/logs/backups/{filename} | 下载备份文件 |
| DELETE | /api/v1/admin/logs/backups/{filename} | 删除备份文件 |
| POST | /api/v1/admin/logs/backups/cleanup | 手动清理备份 |
| GET | /api/v1/admin/logs/config | 获取备份配置 |
| PUT | /api/v1/admin/logs/config | 更新备份配置 |
| POST | /api/v1/admin/logs/backup/{module} | 手动备份模块日志 |

### 6.2 日志内容API参数

```
GET /api/v1/admin/logs/content
参数:
  - file_path: 日志文件名 (必填)
  - start_line: 起始行号 (默认0)
  - max_lines: 最大读取行数 (默认500, 最大2000)
  - level: 日志级别过滤 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - keyword: 关键词搜索
```

### 6.3 备份内容API参数

```
GET /api/v1/admin/logs/backup-content
参数:
  - filename: 备份文件名 (必填)
  - start_line: 起始行号 (默认0)
  - max_lines: 最大读取行数 (默认500, 最大2000)
  - level: 日志级别过滤 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - keyword: 关键词搜索
```

### 6.4 请求示例

```bash
# 获取日志文件列表
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/admin/logs/files

# 获取日志内容（支持分页和过滤）
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/admin/logs/content?file_path=auth.log&level=ERROR&keyword=failed&start_line=0&max_lines=100"

# 获取统计信息
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/admin/logs/stats

# 更新备份配置
curl -X PUT -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"max_file_size_mb": 20, "max_backup_files": 50}' \
  http://localhost:8000/api/v1/admin/logs/config
```

---

## 七、Web管理界面

### 7.1 功能概览

管理员登录后访问 `/admin/logs` 进入日志管理页面：

1. **统计概览** - 显示日志文件数、备份数、大小统计
2. **日志文件列表** - 导出、查看、搜索、备份各模块日志
3. **备份管理** - 查看、下载、删除备份文件
4. **配置管理** - 调整自动备份参数

### 7.2 日志文件列表操作

| 操作 | 说明 |
|------|------|
| 导出 | 下载完整日志文件到本地 |
| 查看 | 在弹窗中查看日志内容，支持级别过滤和关键词搜索 |
| 备份 | 手动备份指定模块的日志 |

### 7.3 日志查看器

```
┌──────────────────────────────────────────────────────────────┐
│  查看日志 - auth                                              │
├──────────────────────────────────────────────────────────────┤
│  [级别过滤 ▼]  [搜索框_______________]  [搜索]    共 1234 行 │
├──────────────────────────────────────────────────────────────┤
│  █ 001 │ 2026-04-17 23:38:01 │ INFO  │ auth:45  │ 认证成功   │
│  █ 002 │ 2026-04-17 23:38:02 │ ERROR │ auth:67  │ API Key无效│
│  █ 003 │ 2026-04-17 23:38:03 │ WARN  │ auth:89  │ 尝试次数过多│
│  █ ...                                                       │
│                                                              │
│  [加载更多...]                                                │
└──────────────────────────────────────────────────────────────┘
```

### 7.4 备份查看器

备份文件查看器与日志查看器功能相同：

```
┌──────────────────────────────────────────────────────────────┐
│  查看备份 - api_platform_20260418_194530.log                   │
├──────────────────────────────────────────────────────────────┤
│  [级别过滤 ▼]  [搜索框_______________]  [搜索]    共 5678 行 │
├──────────────────────────────────────────────────────────────┤
│  █ 001 │ 2026-04-18 19:45:30 │ INFO  │ api:45   │ 系统启动   │
│  █ 002 │ 2026-04-18 19:45:31 │ ERROR │ api:67   │ 数据库连接 │
│  █ ...                                                       │
│                                                              │
│  [加载更多...]                                                │
└──────────────────────────────────────────────────────────────┘
```

### 7.5 备份设置

| 参数 | 说明 | 范围 |
|------|------|------|
| 启用自动备份 | 开启/关闭自动备份 | 开关 |
| 文件大小限制 | 单个日志超过此大小自动备份 | 1-100 MB |
| 最大备份数量 | 超过此数量自动清理 | 10-500 |
| 自动清理 | 启用后自动删除旧备份 | 开关 |
| 清理阈值 | 当达到最大数量的X%时清理 | 50-100% |

---

## 八、自动备份机制

### 8.1 触发条件

日志文件满足以下任一条件时自动备份：

1. 文件大小超过配置的 `max_file_size_mb`
2. Python RotatingFileHandler 触发轮转

### 8.2 备份流程

```
日志文件 > max_file_size_mb
    ↓
复制到 backups/{module}_{timestamp}.log
    ↓
清空原日志文件
    ↓
检查是否超过 max_backup_files
    ↓
超过阈值 → 删除最旧的备份
```

### 8.3 备份文件名格式

```
{模块名}_{年}{月}{日}_{时}{分}{秒}.log

示例:
- api_platform_20260418_194500.log
- auth_20260418_195500.log
- billing_20260418_201000.log
```

---

## 九、中间件日志示例

请求日志自动记录到 `logs/modules/server_middleware_{yyyymmdd}.log`：

**格式**: `yyyy-mm-dd HH:mm:ss.fff | [SERVER] | [SRV-API] | 级别 | 模块:行号 | 消息`

```
2026-04-18 19:49:30.123 | [SERVER] | [SRV-API] | INFO     | api_platform.middleware:52 | Request completed: POST /api/v1/auth/login -> 200 (125.50ms)
2026-04-18 19:49:31.456 | [SERVER] | [SRV-API] | WARNING  | api_platform.middleware:52 | Request completed: POST /api/v1/billing/recharge -> 400 (45.20ms)
2026-04-18 19:49:32.789 | [SERVER] | [SRV-API] | ERROR    | api_platform.middleware:52 | Request completed: GET /api/v1/users/me -> 500 (2340.00ms)
```

---

## 十、调试技巧

### 10.1 查看模块日志

```bash
# Windows CMD
type logs\modules\auth.log

# Windows PowerShell 实时跟踪
Get-Content logs/modules/auth.log -Wait -Tail 50

# PowerShell 查看错误
Select-String -Path "logs/modules/auth.log" -Pattern "ERROR"
```

### 10.2 按级别过滤

```powershell
# 只看 INFO 和 WARNING
Select-String -Path "logs/api_platform.log" -Pattern "\| INFO\s*\|\|\| WARNING\s*\|"

# 只看 ERROR 和 CRICAL
Select-String -Path "logs/api_platform.log" -Pattern "\| ERROR\s*\||CRITICAL\s*\|"
```

### 10.3 按时间过滤

```powershell
# 查看最近1小时的日志
$cutoff = (Get-Date).AddHours(-1)
Get-Content logs/api_platform.log | Where-Object { $_ -match $cutoff.ToString("yyyy-MM-dd HH") }
```

### 10.4 统计日志

```powershell
# 统计错误数量
$errors = Select-String -Path "logs/api_platform.log" -Pattern "ERROR"
Write-Host "错误总数: $($errors.Count)"

# 统计API调用次数
$requests = Select-String -Path "logs/modules/middleware.log" -Pattern "Request completed"
Write-Host "请求总数: $($requests.Count)"
```

---

## 十一、生产环境建议

### 11.1 推荐配置

```env
# 生产环境配置
LOG_LEVEL=WARNING
LOG_ENABLE_CONSOLE=false
LOG_ENABLE_FILE=true
LOG_ROTATION=time

# 备份配置
LOG_BACKUP_MAX_SIZE_MB=10
LOG_BACKUP_MAX_FILES=50
LOG_BACKUP_AUTO_CLEANUP=true
LOG_BACKUP_ENABLED=true
```

### 11.2 日志保留策略

| 环境 | 保留时间 | 建议 |
|------|----------|------|
| 开发 | 7 天 | 可用 size 轮转 |
| 测试 | 14 天 | 时间 + size 轮转 |
| 生产 | 90 天 | 时间轮转 + 归档 |

### 11.3 结构化日志 (JSON)

如需集成 ELK/Sentry，建议输出 JSON 格式：

```python
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        })
```

---

## 十二、安全注意事项

**禁止记录**:
- 用户密码 `password`, `pwd`
- API Secret Key
- 信用卡号、身份证号
- 敏感的个人信息

**正确示例**:
```python
# 错误 ❌
logger.info("用户登录: %s, 密码: %s", email, password)

# 正确 ✓
logger.info("用户登录尝试: %s", email)
```

---

## 十三、常见问题

### Q1: 日志不输出

1. 检查 `LOG_LEVEL` 配置
2. 确认 `LOG_ENABLE_FILE=true`
3. 检查日志目录权限

### Q2: 日志文件过大

```env
# 切换到时间轮转
LOG_ROTATION=time

# 或者减小备份大小限制
LOG_BACKUP_MAX_SIZE_MB=5
```

### Q3: 找不到模块日志

确保 `setup_modules=True` (默认)，日志会写入 `logs/modules/` 目录

### Q4: 备份不生效

1. 检查 `LOG_BACKUP_ENABLED=true`
2. 检查 `logs/backups/` 目录是否存在
3. 确认文件确实超过了 `LOG_BACKUP_MAX_SIZE_MB`

### Q5: Web界面无法访问

1. 确认使用管理员账号登录
2. 检查API服务是否运行
3. 查看浏览器控制台错误信息

---

## 十四、前端日志系统

### 14.1 概述

前端日志系统提供完整的客户端日志记录、错误追踪和用户行为分析功能。

**核心特性**:
- 多级别日志控制 (DEBUG, INFO, WARN, ERROR)
- 本地存储持久化
- 用户行为追踪
- API 请求/响应日志
- 统一的错误提示 UI
- 支持上报到服务器

### 14.2 文件位置

```
web/src/
├── contexts/
│   └── ErrorContext.tsx    # 全局错误处理上下文
├── utils/
│   └── logger.ts          # 日志工具
├── hooks/
│   └── useApi.ts          # API 请求 Hook
└── api/
    └── client.ts          # API 客户端（集成日志）
```

### 14.3 环境变量配置

```env
# .env.example

# 日志级别: debug | info | warn | error
# 开发环境默认 debug，生产环境默认 info
VITE_LOG_LEVEL=debug

# 最大日志条数
VITE_LOG_MAX_SIZE=500

# 是否输出到控制台
VITE_LOG_ENABLE_CONSOLE=true

# 是否保存到本地存储
VITE_LOG_ENABLE_STORAGE=true

# 是否上报到服务器
VITE_LOG_ENABLE_REMOTE=false

# 日志上报地址
VITE_LOG_REMOTE_URL=/api/v1/logs/frontend
```

### 14.4 生产环境配置

```env
# .env.production

# 生产环境使用 INFO 级别，减少日志量
VITE_LOG_LEVEL=info

# 关闭控制台输出（可选）
VITE_LOG_ENABLE_CONSOLE=false

# 开启服务器上报
VITE_LOG_ENABLE_REMOTE=true
VITE_LOG_REMOTE_URL=/api/v1/logs/frontend

# 限制本地存储大小
VITE_LOG_MAX_SIZE=200
```

### 14.5 代码使用

#### 14.5.1 基础日志

```typescript
import { logger, log } from '../utils/logger'

// 使用 logger 单例
logger.debug('调试信息', { key: 'value' })
logger.info('操作成功')
logger.warn('警告信息')
logger.error('错误信息', error)

// 使用快捷方法
log.debug('...')
log.info('...')
log.warn('...')
log.error('...')
```

#### 14.5.2 API 日志

```typescript
// API 请求/响应自动记录
import { api } from '../api/client'

// api.get/post/put/delete 会自动记录请求和响应
const data = await api.get('/users/me')

// 手动记录
logger.logRequest('GET', '/api/endpoint')
logger.logResponse('GET', '/api/endpoint', 200, data)
logger.logApiError('POST', '/api/endpoint', error)
```

#### 14.5.3 用户行为日志

```typescript
import { log } from '../utils/logger'

// 页面访问
log.pageView('/developer/keys')

// 用户操作
log.userAction('click', 'create_key_button')
log.userAction('submit', 'login_form')
log.userAction('navigate', 'billing_page')
```

#### 14.5.4 统一错误处理

```typescript
// 在页面中使用 ErrorProvider 提供的 hook
import { useError } from '../contexts/ErrorContext'

function MyComponent() {
  const { showError, showSuccess, showWarning, showInfo } = useError()

  const handleSubmit = async () => {
    try {
      await api.post('/data', values)
      showSuccess('保存成功')
    } catch (error) {
      // 显示友好的错误弹窗
      showError(error, () => handleSubmit()) // 支持重试
    }
  }
}
```

#### 14.5.5 useApi Hook

```typescript
import { useApi } from '../hooks/useApi'

function MyPage() {
  const { request } = useApi()

  useEffect(() => {
    // 自动处理错误和日志
    request(() => api.getData(), {
      context: 'FetchUserData',
      onSuccess: (data) => console.log(data),
    })
  }, [])

  // 带重试的请求
  const fetchWithRetry = async () => {
    await requestWithRetry(() => api.getData(), 3, 1000, 'FetchData')
  }
}
```

### 14.6 日志格式

**控制台/文件输出格式**:
```
[yyyymmdd HH:mm:ss.fff] [WEB] [级别] [分类] 消息
```

**示例**:
```
[20260418 19:49:30.123] [WEB] [WEB-API] Request POST /api/v1/auth/login
[20260418 19:49:30.456] [WEB] [WEB-API] Response 200 OK
[20260418 19:49:31.789] [WEB] [WEB-API] Response Error 401
[20260418 19:49:32.012] [WEB] [WEB-Page] /developer/keys
[20260418 19:49:33.345] [WEB] [WEB-Action] Click create_key_button
[20260418 19:49:34.567] [WEB] [INFO] [Logger] Logger initialized
[20260418 19:49:35.678] [WEB] [ERROR] [Auth] Login failed
```

**分类标签说明**:

| 标签 | 说明 | 使用场景 |
|------|------|----------|
| `[WEB]` | 前端全局标识 | 所有前端日志行首 |
| `[WEB-API]` | 前端 API 请求/响应 | HTTP 请求、响应、错误 |
| `[WEB-Page]` | 页面访问 | 页面路由切换 |
| `[WEB-Action]` | 用户操作 | 按钮点击、表单提交 |
| `[SERVER]` | 后端全局标识 | 所有后端日志行首 |
| `[SRV-API]` | 后端 API 请求 | 请求处理日志 |

**JSON 存储格式**:
```json
{
  "timestamp": "20260418 19:49:30.123",
  "timestampRaw": "2026-04-18T11:49:30.123Z",
  "level": "ERROR",
  "message": "API request failed",
  "context": "WEB-API",
  "data": { "status": 401 },
  "userId": "user_123",
  "sessionId": "sess_1234567890_abc",
  "url": "/developer/keys"
}
```

### 14.7 动态开关

日志系统支持运行时动态调整：

```typescript
import { log, LogLevel } from '../utils/logger'

// 动态调整日志级别
log.setLevel(LogLevel.DEBUG)  // 开启详细日志
log.setLevel(LogLevel.ERROR)  // 只记录错误

// 获取当前配置
const config = log.getConfig()
console.log(config.level, config.enableRemote)

// 获取日志统计
const stats = log.getStats()
console.log(stats.total, stats.error)
```

### 14.8 日志导出

```typescript
import { log, downloadLogs } from '../utils/logger'

// 导出为文本 (返回 { filename, content })
const text = log.export()
console.log(text.filename) // "web-app-log-20260418-194530.txt"
console.log(text.content)

// 导出为 JSON (返回 { filename, content })
const json = log.exportJson()
console.log(json.filename) // "web-app-log-20260418-194530.json"
console.log(json.content)

// 一键下载日志文件
downloadLogs('txt')  // 下载 txt 文件
downloadLogs('json') // 下载 json 文件

// 清除日志
log.clear()
```

**导出文件示例** (txt 格式):
```
[20260418 19:49:30.123] [WEB] [INFO] [Logger] Logger initialized
[20260418 19:49:31.456] [WEB] [WEB-API] Request POST /api/v1/auth/login
[20260418 19:49:31.789] [WEB] [WEB-API] Response 200 OK {"token": "..."}
[20260418 19:49:32.012] [WEB] [ERROR] [Auth] Login failed {"error": "invalid credentials"}
```

### 14.9 错误类型映射

| HTTP 状态码 | ErrorType | 用户提示 |
|-------------|-----------|----------|
| 401 | AUTH | 登录已过期，请重新登录 |
| 403 | AUTH | 您没有权限执行此操作 |
| 404 | NOT_FOUND | 请求的资源不存在 |
| 422 | VALIDATION | 数据格式不正确 |
| 429 | BUSINESS | 请求过于频繁，请稍后再试 |
| 500 | SERVER | 服务器开小差了，请稍后重试 |
| 0 | NETWORK | 网络连接失败，请检查网络 |

### 14.10 安全注意事项

**禁止记录**:
- 用户密码
- API Secret Key
- 敏感个人信息
- 信用卡号等

**正确示例**:
```typescript
// 错误 ❌
logger.info('User login', { email, password })

// 正确 ✓
logger.info('User login', { email })
```

---

## 十五、更新日志

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-04-19 | v1.5 | 添加日志导出功能和备份查看功能；修复日志解析器支持 [SERVER] 前缀；支持模块日志目录 |
| 2026-04-18 | v1.4 | 日志文件列表支持模块日志；备份查看支持级别过滤和关键词搜索 |
| 2026-04-18 | v1.3 | 日志文件名添加日期和前缀、添加毫秒精度、统一分类标签 |
| 2026-04-18 | v1.2 | 后端日志格式改进，添加 [SERVER] 和 [SRV-API] 标签 |
| 2026-04-18 | v1.1 | 添加前端日志系统、ErrorContext、useApi Hook |
| 2026-04-18 | v1.0 | 初始版本，包含后端日志系统 |

---

## 十六、扩展性和兼容性说明

### 16.1 前端扩展

前端日志系统支持灵活扩展新的分类标签：

```typescript
// 在 logger.ts 中添加新的分类方法
class Logger {
  // 添加新的分类标签
  logCustomTag(tag: string, message: string, data?: any) {
    this.info(`[${tag}]`, message, data)
  }

  // 预设扩展方法示例
  logForm(formName: string, action: string, data?: any) {
    this.info(`[WEB-FORM]`, { form: formName, action, ...data })
  }

  logComponent(componentName: string, event: string, data?: any) {
    this.info(`[WEB-COMP]`, { component: componentName, event, ...data })
  }
}
```

### 16.2 后端扩展

后端日志系统支持灵活添加新的模块：

```python
from src.config.logging_config import setup_module_loggers

# 添加新模块日志
setup_module_loggers(
    root_level="INFO",
    enable_console=True,
    enable_file=True,
    modules=["auth", "billing", "repo", "quota", "api", "middleware", "database", "security", "new_module"]
)

# 使用新模块日志
logger = get_logger("new_module")
logger.info("新模块日志示例")
```

### 16.3 兼容性处理

**后端文件读取兼容**:

```python
# 自动检测新旧文件名格式
def get_log_files():
    today = datetime.now().strftime("%Y%m%d")
    new_name = f"server_api_platform_{today}.log"
    old_name = "api_platform.log"
    old_name_alt = f"api_platform_{today}.log"

    # 按优先级尝试读取
    if Path(LOG_DIR / new_name).exists():
        return new_name
    elif Path(LOG_DIR / old_name).exists():
        return old_name
    elif Path(LOG_DIR / old_name_alt).exists():
        return old_name_alt
    return None
```

**日志分析工具兼容**:

新旧日志格式均可通过正则匹配:

```python
import re

# 新格式 (带毫秒和 [SERVER] 前缀)
new_pattern = r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+\|\s+\[SERVER\]\s+\|\s+(\w+)\s+\|\s+([^|]+)\s+\|\s+(.*)$'

# 旧格式 (无毫秒和前缀)
old_pattern = r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*\|\s*(\w+)\s*\|\s*([^|]+):(\d+)\s*\|\s*(.*)$'
```
