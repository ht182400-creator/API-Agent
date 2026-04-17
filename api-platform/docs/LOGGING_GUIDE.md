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
├── api_platform.log              # 主日志 (所有模块汇总)
├── api_platform.log.1            # 轮转备份
├── api_platform.log.2            # ...
├── backup_config.json            # 备份配置文件
├── modules/                      # 模块分解日志
│   ├── auth.log                  # 认证模块日志
│   ├── billing.log               # 计费模块日志
│   ├── middleware.log            # 中间件日志
│   ├── repo.log                  # 仓库模块日志
│   ├── quota.log                 # 配额模块日志
│   ├── api.log                   # API模块日志
│   ├── database.log              # 数据库模块日志
│   └── security.log              # 安全模块日志
└── backups/                      # 自动备份目录
    ├── api_platform_20260417_234500.log    # 主日志备份
    ├── auth_20260417_234500.log            # 模块日志备份
    └── ...
```

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
| GET | /api/v1/admin/logs/content | 获取日志内容 |
| GET | /api/v1/admin/logs/stats | 获取日志统计 |
| GET | /api/v1/admin/logs/backups | 获取备份文件列表 |
| GET | /api/v1/admin/logs/backups/{filename} | 下载备份文件 |
| DELETE | /api/v1/admin/logs/backups/{filename} | 删除备份文件 |
| POST | /api/v1/admin/logs/backups/cleanup | 手动清理备份 |
| GET | /api/v1/admin/logs/config | 获取备份配置 |
| PUT | /api/v1/admin/logs/config | 更新备份配置 |
| POST | /api/v1/admin/logs/backup/{module} | 手动备份模块日志 |

### 6.2 请求示例

```bash
# 获取日志文件列表
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/v1/admin/logs/files

# 获取日志内容（支持分页和过滤）
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/v1/admin/logs/content?file_path=auth.log&level=ERROR&keyword=failed&start_line=0&max_lines=100"

# 获取统计信息
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/v1/admin/logs/stats

# 更新备份配置
curl -X PUT -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"max_file_size_mb": 20, "max_backup_files": 50}' \
  http://localhost:8080/api/v1/admin/logs/config
```

---

## 七、Web管理界面

### 7.1 功能概览

管理员登录后访问 `/admin/logs` 进入日志管理页面：

1. **统计概览** - 显示日志文件数、备份数、大小统计
2. **日志文件列表** - 查看、搜索、备份各模块日志
3. **备份管理** - 查看、下载、删除备份文件
4. **配置管理** - 调整自动备份参数

### 7.2 日志查看器

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

### 7.3 备份设置

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
- api_platform_20260417_234500.log
- auth_20260417_235500.log
- billing_20260418_001000.log
```

---

## 九、中间件日志示例

请求日志自动记录到 `logs/modules/middleware.log`：

```
2026-04-17 23:38:01 | INFO     | api_platform.middleware:39 | Request completed: POST /api/v1/auth/login -> 200 (125.50ms)
2026-04-17 23:38:02 | WARNING  | api_platform.middleware:39 | Request completed: POST /api/v1/billing/recharge -> 400 (45.20ms)
2026-04-17 23:38:03 | ERROR    | api_platform.middleware:39 | Request completed: GET /api/v1/users/me -> 500 (2340.00ms)
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
