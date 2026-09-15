@echo off
chcp 65001 >nul
setlocal EnableExtensions

REM ============================================================================
REM  API Platform - 后端服务启动脚本 (Windows)
REM ----------------------------------------------------------------------------
REM  功能：
REM    1) 结束旧的 uvicorn 后端进程（含 --reload 的父进程与子进程）
REM    2) 兜底释放 8000 端口
REM    3) 启动 FastAPI 后端服务
REM
REM  用法：双击本文件，或在命令行执行  start-backend.bat
REM  访问：http://localhost:8000/docs
REM ============================================================================

REM 切换到脚本所在目录（api-platform）
cd /d "%~dp0"

set "PORT=8000"
set "HOST=0.0.0.0"

title API Platform - 后端服务 (%PORT%)

echo ============================================================
echo   API Platform - 后端服务启动器
echo ============================================================
echo   项目目录 : %CD%
echo   监听端口 : %PORT%
echo.

REM ---------------------------------------------------------------------------
REM 0. 环境检查
REM ---------------------------------------------------------------------------
where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 python 命令。
    echo        请安装 Python 3.11+ 并将其加入系统 PATH。
    echo.
    pause
    exit /b 1
)

if not exist "src\main.py" (
    echo [错误] 当前目录未找到 src\main.py
    echo        请确认本脚本位于 api-platform 目录下。
    echo.
    pause
    exit /b 1
)

REM ---------------------------------------------------------------------------
REM 1. 结束旧的后端进程
REM    按命令行精确匹配 uvicorn / src.main，避免误杀其他 Python 程序；
REM    同时结束其子进程（uvicorn --reload 在 Windows 下的工作进程）。
REM ---------------------------------------------------------------------------
echo [1/3] 清理旧的后端进程 ...

powershell -NoProfile -ExecutionPolicy Bypass -Command "$procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue; $targets = @($procs | Where-Object { ($_.Name -like 'python*' -or $_.Name -like 'uvicorn*') -and $_.CommandLine -and ($_.CommandLine -match 'uvicorn' -or $_.CommandLine -match 'src\.main') }); $ids = @($targets | Select-Object -ExpandProperty ProcessId); $children = @($procs | Where-Object { $ids -contains $_.ParentProcessId } | Select-Object -ExpandProperty ProcessId); $all = @($ids + $children | Sort-Object -Unique); if ($all.Count -eq 0) { Write-Host '       未发现旧的后端进程' } else { foreach ($id in $all) { if ($id -gt 0) { Write-Host ('       结束进程 PID=' + $id); Stop-Process -Id $id -Force -ErrorAction SilentlyContinue } } }"

REM ---------------------------------------------------------------------------
REM 2. 兜底：释放仍被占用的 8000 端口
REM ---------------------------------------------------------------------------
echo [2/3] 检查端口 %PORT% 占用情况 ...

set "PORT_BUSY="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:"LISTENING" ^| findstr ":%PORT% "') do (
    if not "%%p"=="0" (
        echo       端口 %PORT% 仍被 PID=%%p 占用，强制结束
        taskkill /F /T /PID %%p >nul 2>&1
        set "PORT_BUSY=1"
    )
)
if not defined PORT_BUSY echo       端口 %PORT% 已就绪

REM 等待端口完全释放
ping -n 2 127.0.0.1 >nul 2>&1

REM ---------------------------------------------------------------------------
REM 3. 启动后端服务
REM ---------------------------------------------------------------------------
echo.
echo [3/3] 启动后端服务 ...
echo       API 文档  : http://localhost:%PORT%/docs
echo       健康检查 : http://localhost:%PORT%/health
echo       停止服务 : 按 Ctrl+C
echo ------------------------------------------------------------
echo.

REM 统一使用 UTF-8，避免 Windows 控制台中文日志乱码
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

python -m uvicorn src.main:app --reload --host %HOST% --port %PORT%

echo.
echo ============================================================
echo   后端服务已退出（退出码 %ERRORLEVEL%）
echo ============================================================
pause
endlocal
