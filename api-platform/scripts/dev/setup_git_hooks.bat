@echo off
chcp 936 >nul
REM ============================================================================
REM  启用 Git hooks —— 提交前类型检查防线
REM
REM 【重要】编码约定：本文件必须保存为 ANSI / GBK(CP936) + CRLF 换行。
REM   若另存为 UTF-8，cmd 会按 GBK 解码中文字节 -> 注释乱码，
REM   且 REM 行可能被当成命令执行（现象："xxx 不是内部或外部命令"）。
REM ----------------------------------------------------------------------------
REM  作用：把仓库内的 .githooks/ 挂载为 Git hooks 目录。
REM        启用后，每次提交若涉及 api-platform/web/src 下的 .ts/.tsx 变更，
REM        会自动执行 `tsc --noEmit`，不通过则拒绝提交。
REM
REM  背景：2026-09-15 发现 permissionHooks.ts 中写了 JSX（应为 .tsx），
REM        这一个语法错误让 TypeScript 跳过全部语义检查，
REM        导致 48 个类型错误长期隐身。CI 早已配置 tsc 检查，
REM        但项目为本地开发、未触发过 Actions，因此需要本地防线。
REM
REM  用法（每次 clone 后执行一次即可）：
REM      双击本文件，或在命令行运行：
REM      api-platform\scripts\dev\setup_git_hooks.bat
REM
REM  临时跳过检查（不推荐）：git commit --no-verify
REM ============================================================================

cd /d "%~dp0..\..\.."
echo [setup] 仓库根目录: %CD%

git config core.hooksPath .githooks
if errorlevel 1 (
    echo [ERROR] 设置 core.hooksPath 失败，请检查是否在 Git 仓库内
    exit /b 1
)

echo [OK] 已启用 Git hooks（core.hooksPath = .githooks）
echo      提交涉及前端 TS/TSX 时将自动执行 tsc --noEmit
echo.
echo 验证方式：git config --get core.hooksPath
exit /b 0
