"""Test package.

注意：本文件必须保持为空（仅包标记）。
所有 pytest fixtures 统一定义在 tests/conftest.py 中。

历史问题：本文件曾误将 conftest 内容（含 `from src.main import app`）复制进来，
导致 pytest 在收集阶段导入 `tests` 包时就触发应用初始化与日志初始化，
进而关闭真实 stdout，使 pytest 报
`ValueError: I/O operation on closed file` 并收集到 0 个用例。
详见 docs/ENVIRONMENT_AND_PAYMENT_MODE.md「附：测试环境修复记录」。
"""
