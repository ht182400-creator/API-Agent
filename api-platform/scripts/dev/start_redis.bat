@echo off
chcp 936 >nul
REM ==============================================================================
REM 启动 WSL 内的 Redis（本地开发用）
REM
REM 【重要】编码约定（2026-09-15 修复桌面启动乱码）：
REM   本文件必须保存为 ANSI / GBK(CP936) 编码 + CRLF 换行。
REM   若被编辑器另存为 UTF-8，cmd 会按 GBK 解码中文字节 ->
REM   显示乱码，并把 REM 注释行当成命令执行
REM   （现象："'localhost' 不是内部或外部命令"）。
REM
REM 背景：
REM   Redis 安装在 WSL (Ubuntu-20.04) 内，Windows 通过 WSL2 localhost 转发访问。
REM   两个关键点：
REM     1. WSL 发行版在无活动会话后会自动关闭 -> Redis 随之消失
REM        （现象：应用报 Redis Timeout，但 wslrelay 监听还在）
REM        因此需要 sleep infinity 常驻保活。
REM     2. WSL2 的 localhost 转发不覆盖绑定在 127.0.0.1 的服务，
REM        故 redis.conf 已改为 bind 0.0.0.0 + requirepass（密码见 .env 的 REDIS_URL）。
REM
REM 用法：重启电脑 / WSL 关闭后运行本脚本即可。
REM ==============================================================================

echo [1/3] 启动 WSL 中的 Redis ...
wsl -u root -e bash -c "service redis-server start"
if errorlevel 1 (
    echo [错误] Redis 启动失败，请检查 WSL 状态（wsl -l -v）
    exit /b 1
)

echo [2/3] 启动 WSL 保活进程（防止空闲自动关闭）...
start /min "" wsl --exec sleep infinity

echo [3/3] 验证连接 ...
timeout /t 2 /nobreak >nul
wsl -e redis-cli -a redis123 ping 2>nul

echo.
echo [完成] Redis 应已就绪（Windows 侧 127.0.0.1:6379，密码见 .env REDIS_URL）
