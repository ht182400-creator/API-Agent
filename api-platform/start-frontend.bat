@echo off
chcp 65001 >nul
setlocal EnableExtensions

REM ============================================================================
REM  API Platform - 前端服务启动脚本 (Windows)
REM ----------------------------------------------------------------------------
REM  功能：
REM    1) 结束旧的 Vite 前端进程（含其子进程）
REM    2) 启动前端开发服务器（npm run dev）
REM
REM  用法：双击本文件，或在命令行执行  start-frontend.bat
REM  访问：http://localhost:3000 （端口由 portfinder 从 3000 起自动探测）
REM
REM  说明：前端需先启动后端（start-backend.bat），
REM        请求 /api 会被 Vite 代理到 http://localhost:8000
REM ============================================================================

REM 切换到脚本所在目录的前端工程（api-platform\web）
cd /d "%~dp0web"

title API Platform - 前端服务 (Vite)

echo ============================================================
echo   API Platform - 前端服务启动器
echo ============================================================
echo   前端目录 : %CD%
echo   默认地址 : http://localhost:3000
echo.

REM ---------------------------------------------------------------------------
REM 0. 环境检查
REM ---------------------------------------------------------------------------
if not exist "package.json" (
    echo [错误] 当前目录未找到 package.json
    echo        请确认 web 目录存在，且本脚本位于 api-platform 目录下。
    echo.
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 npm 命令。
    echo        请安装 Node.js 18+ 并将其加入系统 PATH。
    echo.
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo [提示] 未检测到 node_modules，请先安装依赖：
    echo.
    echo         cd /d "%CD%"
    echo         npm install
    echo.
    pause
    exit /b 1
)

REM ---------------------------------------------------------------------------
REM 1. 结束旧的前端进程
REM    按命令行匹配 "vite" + "api-platform"，精确定位本项目的 Vite 进程，
REM    避免误杀其他 Node 程序；同时结束其子进程。
REM ---------------------------------------------------------------------------
echo [1/2] 清理旧的前端进程 ...

powershell -NoProfile -ExecutionPolicy Bypass -Command "$procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue; $targets = @($procs | Where-Object { $_.Name -like 'node*' -and $_.CommandLine -and $_.CommandLine -match 'vite' -and $_.CommandLine -match 'api-platform' }); $ids = @($targets | Select-Object -ExpandProperty ProcessId); $children = @($procs | Where-Object { $ids -contains $_.ParentProcessId } | Select-Object -ExpandProperty ProcessId); $all = @($ids + $children | Sort-Object -Unique); if ($all.Count -eq 0) { Write-Host '       未发现旧的前端进程' } else { foreach ($id in $all) { if ($id -gt 0) { Write-Host ('       结束进程 PID=' + $id); Stop-Process -Id $id -Force -ErrorAction SilentlyContinue } } }"

REM 等待端口与句柄释放
ping -n 2 127.0.0.1 >nul 2>&1

REM ---------------------------------------------------------------------------
REM 2. 启动前端开发服务器
REM ---------------------------------------------------------------------------
echo.
echo [2/2] 启动前端开发服务器 ...
echo       访问地址 : http://localhost:3000
echo       提示     : 若 3000 端口被占用，Vite 会自动切换到 3001 及之后端口
echo       停止服务 : 按 Ctrl+C
echo ------------------------------------------------------------
echo.

npm run dev

echo.
echo ============================================================
echo   前端服务已退出（退出码 %ERRORLEVEL%）
echo ============================================================
pause
endlocal
