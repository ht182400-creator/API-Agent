# Python 缓存导致代码修改不生效问题

## 问题描述

修改后端代码后，API 请求仍然报错：
```
NameError: name 'logger' is not defined
```

虽然代码中 `logger` 已正确定义，但服务加载的是旧版本的模块。

## 根本原因

Python 的 `__pycache__` 目录会缓存编译后的 `.pyc` 文件。当代码修改后，如果服务没有使用 `--reload` 参数启动，Python 仍然加载缓存的旧代码版本。

### 错误日志位置
- 主日志: `logs/server_api_platform_YYYYMMDD.log`
- 错误日志: `logs/errors_YYYYMMDD.log`

## 解决方案

### 步骤 1: 停止后端服务

找到并停止所有 Python 进程：
```powershell
# 查看 Python 进程
Get-Process python

# 停止指定进程
Stop-Process -Id <PID> -Force
```

### 步骤 2: 清除 Python 缓存

删除所有 `__pycache__` 目录：
```powershell
# 在项目根目录执行
Get-ChildItem -Path . -Include __pycache__ -Recurse -Directory | Remove-Item -Recurse -Force
```

或者手动删除：
```powershell
# 在 api-platform 目录执行
Remove-Item -Recurse -Force __pycache__
Remove-Item -Recurse -Force src/__pycache__
Remove-Item -Recurse -Force src/*/__pycache__
```

### 步骤 3: 重新启动服务

使用 `--reload` 参数启动，以便代码修改后自动重载：
```powershell
cd d:\Work_Area\AI\API-Agent\api-platform
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 验证服务正常运行

```powershell
# 测试 API 文档页面
Invoke-RestMethod -Uri 'http://localhost:8000/docs'

# 检查日志确认启动成功
Get-Content logs/server_api_platform_20260508.log -Tail 10
```

正常日志应显示：
```
2026-05-08 09:49:07.496 | [SERVER] | INFO | Starting API Platform...
2026-05-08 09:49:07.565 | [SERVER] | INFO | Database initialized
```

## 预防措施

### 1. 开发环境始终使用 --reload

```powershell
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

`--reload` 参数会在检测到代码变化时自动重启服务。

### 2. 修改代码后注意观察日志

如果使用 `--reload`，修改代码后控制台会显示：
```
INFO:     Detected change in 'src/api/v1/payment.py', reloading...
INFO:     Successfully reloaded
```

### 3. 遇到异常时先清除缓存

如果遇到奇怪的错误（如变量未定义、导入失败等），先尝试：
```powershell
# 清除所有 Python 缓存
Get-ChildItem -Path . -Include __pycache__,.pytest_cache -Recurse -Directory | Remove-Item -Recurse -Force
```

### 4. 定期清理旧日志

日志文件会不断增长，可以定期清理：
```powershell
# 保留最近 7 天的日志
$cutoff = (Get-Date).AddDays(-7)
Get-ChildItem logs/*.log | Where-Object { $_.LastWriteTime -lt $cutoff } | Remove-Item
```

## 相关文件

- 日志配置: `src/config/logging_config.py`
- 日志目录: `api-platform/logs/`
- 主入口: `src/main.py`

## 记录信息

- 问题发生时间: 2026-05-08 09:47
- 问题解决时间: 2026-05-08 09:49
- 受影响文件: `src/api/v1/payment.py`
- 错误类型: `NameError: name 'logger' is not defined`
