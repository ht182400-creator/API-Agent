"""
一次性清理脚本：删除 RepoService 中的死代码链。

背景（2026-09-15 取证结论，详见 docs/OPTIMIZATION_BACKLOG.md §2.9.1）：

    RepoService（类）            ← 全项目 0 处实例化（仅 services/__init__.py 导出）
      └─ call_repository()       ← 全项目 0 处调用
           ├─ check_rate_limit()          ← 0 处调用
           ├─ _build_auth_headers()       ← 仅 call_repository 内部调用
           ├─ _log_api_call()             ← 仅 call_repository 内部调用
           └─ _process_billing()          ← 仅 call_repository 内部调用
                └─ _deduct_balance()      ← 构造 Bill(account_id=...) 字段不存在，必抛 TypeError

    真实的仓库转发与扣费由 `src/api/v1/repositories.py` 承担（该实现正确传入 environment）。

删除范围：自 `async def call_repository(` 起，至 `async def get_repo_stats(` 之前的一整段连续区块。

用法：
    cd api-platform
    python scripts/dev/remove_dead_repo_service_code.py
"""

from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "src" / "services" / "repo_service.py"

START_MARKER = "    async def call_repository("
END_MARKER = "    async def get_repo_stats("


def main() -> None:
    source = TARGET.read_text(encoding="utf-8")

    if START_MARKER not in source:
        print("[SKIP] 未找到起始标记，可能已删除过，无需处理")
        return

    if END_MARKER not in source:
        raise SystemExit("[ERROR] 未找到结束标记，请人工确认文件结构")

    start = source.index(START_MARKER)
    end = source.index(END_MARKER)

    if not (0 < start < end):
        raise SystemExit("[ERROR] 标记位置异常，已中止")

    removed_block = source[start:end]
    removed_lines = removed_block.count("\n")

    TARGET.write_text(source[:start] + source[end:], encoding="utf-8")

    print(f"[OK] 已删除死代码链，共 {removed_lines} 行")
    print(f"     文件：{TARGET}")


if __name__ == "__main__":
    main()
