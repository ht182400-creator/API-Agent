"""
初始化日志目录和配置
运行此脚本确保日志系统正确初始化

使用方法:
    python scripts/init_logs.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.logging_config import LOG_DIR, MODULE_LOG_DIR, setup_logger


def init_logs():
    """初始化日志目录"""
    print("Initializing log directories...")

    # 创建日志目录
    LOG_DIR.mkdir(exist_ok=True)
    print(f"  Created: {LOG_DIR}")

    # 创建模块日志目录
    MODULE_LOG_DIR.mkdir(exist_ok=True)
    print(f"  Created: {MODULE_LOG_DIR}")

    # 创建 .gitkeep 文件确保目录被版本控制
    (LOG_DIR / ".gitkeep").touch()
    (MODULE_LOG_DIR / ".gitkeep").touch()

    print("Log directories initialized!")


def show_log_structure():
    """显示日志目录结构"""
    print("\nLog Directory Structure:")
    print("=" * 50)

    # 主日志目录
    for f in LOG_DIR.iterdir():
        if f.name != ".gitkeep":
            size = f.stat().st_size if f.is_file() else 0
            print(f"  {f.name} ({size:,} bytes)")

    # 模块日志目录
    if MODULE_LOG_DIR.exists():
        for f in MODULE_LOG_DIR.iterdir():
            if f.name != ".gitkeep":
                print(f"  modules/{f.name}")

    print("=" * 50)


if __name__ == "__main__":
    init_logs()
    show_log_structure()

    print("\nLog system ready!")
    print(f"Main log: {LOG_DIR / 'api_platform.log'}")
    print(f"Module logs: {MODULE_LOG_DIR}")
