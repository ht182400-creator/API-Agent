"""
日志配置模块 - 支持多级别、按模块分解日志、自动备份

功能:
    - 多级别日志控制 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - 按模块分解日志文件
    - 控制台和文件双输出
    - 自动备份机制（大小超限自动备份）
    - 日志轮转保护

使用示例:
    # 1. 主日志记录器
    from src.config.logging_config import logger
    logger.info("消息")

    # 2. 模块级日志记录器 (自动按模块输出)
    from src.config.logging_config import get_logger
    logger = get_logger("auth_service")
    logger.info("认证信息")

    # 3. 快捷函数
    from src.config.logging_config import log_info, log_error
    log_info("消息")
    log_error("错误")

日志文件结构:
    logs/
    ├── api_platform.log              # 主日志
    ├── modules/
    │   ├── auth.log                  # 认证模块
    │   ├── billing.log               # 计费模块
    │   └── ...
    └── backups/
        ├── api_platform_20240101_120000.log      # 主日志备份
        ├── auth_20240101_120000.log              # 模块日志备份
        └── ...
"""

import logging
import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Dict, Optional, List, Any
import threading

# 日志目录
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 模块日志目录
MODULE_LOG_DIR = LOG_DIR / "modules"
MODULE_LOG_DIR.mkdir(exist_ok=True)

# 备份目录
BACKUP_DIR = LOG_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)


class LogConfig:
    """日志配置类"""

    # 日志级别映射
    LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    # 级别颜色 (用于前端显示)
    LEVEL_COLORS = {
        "DEBUG": "#1890ff",    # 蓝色
        "INFO": "#52c41a",     # 绿色
        "WARNING": "#faad14",  # 橙色
        "ERROR": "#ff4d4f",    # 红色
        "CRITICAL": "#722ed1", # 紫色
    }

    # 默认配置
    DEFAULT_LEVEL = "INFO"
    DEFAULT_FORMAT = "%(asctime)s.%(msecs)03d | [SERVER] | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    # 日志前缀
    LOG_PREFIX = "[SERVER]"

    # 文件大小限制: 10MB (默认)
    MAX_BYTES = 10 * 1024 * 1024
    # 保留文件数量 (默认30个)
    BACKUP_COUNT = 30
    # 最大备份文件数量 (超过此数量自动清理)
    MAX_BACKUP_FILES = 100

    # 按时间轮转: 每天
    WHEN = "midnight"
    INTERVAL = 1


class LogBackupManager:
    """日志备份管理器 - 自动管理日志文件备份"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """从配置文件加载备份设置"""
        config_path = LOG_DIR / "backup_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "max_file_size_mb": 10,           # 单个日志文件最大10MB
            "max_backup_files": 100,           # 最多保留100个备份文件
            "auto_cleanup": True,              # 自动清理旧备份
            "cleanup_threshold": 80,           # 超过80个文件时清理
            "enabled": True                   # 启用自动备份
        }

    def save_config(self, config: Dict[str, Any]):
        """保存配置"""
        self._config.update(config)
        config_path = LOG_DIR / "backup_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    @property
    def config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self._config.copy()

    def get_max_size_bytes(self) -> int:
        """获取最大文件大小(字节)"""
        return self._config.get("max_file_size_mb", 10) * 1024 * 1024

    def should_backup(self, file_path: Path) -> bool:
        """检查是否需要备份"""
        if not self._config.get("enabled", True):
            return False
        if not file_path.exists():
            return False
        max_size = self.get_max_size_bytes()
        return file_path.stat().st_size >= max_size

    def perform_backup(self, file_path: Path) -> Optional[Path]:
        """执行备份"""
        if not file_path.exists():
            return None

        # 生成备份文件名: 原名_YYYYMMDD.log (简化格式，包含日期)
        date_str = datetime.now().strftime("%Y%m%d")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        module_name = file_path.stem
        
        # 检查当日是否已有备份文件
        today_backup_pattern = f"{module_name}_{date_str}*.log"
        existing_backups = list(BACKUP_DIR.glob(today_backup_pattern))
        
        # 如果当日已有备份，追加序号
        if existing_backups:
            backup_name = f"{module_name}_{timestamp}.log"
        else:
            # 当日第一份备份
            backup_name = f"{module_name}_{date_str}.log"
        
        backup_path = BACKUP_DIR / backup_name

        try:
            # 复制文件到备份目录
            import shutil
            shutil.copy2(file_path, backup_path)
            
            # 清空原文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("")
            
            # 检查并清理旧备份
            self._cleanup_old_backups()
            
            return backup_path
        except Exception as e:
            logging.error(f"备份日志文件失败: {e}")
            return None

    def _cleanup_old_backups(self):
        """清理旧备份文件"""
        if not self._config.get("auto_cleanup", True):
            return

        max_files = self._config.get("max_backup_files", 100)
        cleanup_threshold = self._config.get("cleanup_threshold", 80)

        # 获取所有备份文件
        backup_files = sorted(
            BACKUP_DIR.glob("*.log"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        # 如果超过阈值，删除最旧的文件
        if len(backup_files) > max_files:
            files_to_delete = backup_files[max_files:]
            for f in files_to_delete:
                try:
                    f.unlink()
                except Exception:
                    pass

    def get_backup_files(self) -> List[Dict[str, Any]]:
        """获取所有备份文件信息"""
        backups = []
        for f in sorted(BACKUP_DIR.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True):
            stat = f.stat()
            backups.append({
                "name": f.name,
                "path": str(f),
                "size": stat.st_size,
                "size_formatted": self._format_size(stat.st_size),
                "created_at": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
        return backups

    def delete_backup(self, filename: str) -> bool:
        """删除指定的备份文件"""
        backup_path = BACKUP_DIR / filename
        if backup_path.exists() and backup_path.parent == BACKUP_DIR:
            try:
                backup_path.unlink()
                return True
            except Exception:
                return False
        return False

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


class ColoredFormatter(logging.Formatter):
    """彩色格式化器 (用于控制台)"""

    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
        'RESET': '\033[0m',
    }

    def format(self, record):
        if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
            return super().format(record)

        levelname = record.levelname
        color = self.COLORS.get(levelname, self.COLORS['RESET'])
        record.levelname = f"{color}{levelname}{self.COLORS['RESET']}"

        return super().format(record)


class AutoBackupRotatingFileHandler(RotatingFileHandler):
    """支持自动备份的文件处理器"""

    def __init__(self, *args, **kwargs):
        self.backup_manager = LogBackupManager()
        super().__init__(*args, **kwargs)

    def shouldRollover(self, record) -> int:
        """检查是否需要轮转"""
        # 先检查原始逻辑
        if super().shouldRollover(record):
            return 1
        
        # 检查是否需要自动备份
        if self.backup_manager.should_backup(Path(self.baseFilename)):
            return 1
        
        return 0

    def doRollover(self):
        """执行轮转"""
        # 执行父类的轮转
        super().doRollover()
        
        # 执行自动备份
        self.backup_manager.perform_backup(Path(self.baseFilename))


def setup_module_loggers(
    root_level: str = "INFO",
    enable_console: bool = True,
    enable_file: bool = True,
    modules: list = None
):
    """
    设置模块级日志记录器

    Args:
        root_level: 根日志级别
        enable_console: 是否输出到控制台
        enable_file: 是否输出到文件
        modules: 要设置的模块列表，默认包含核心模块
    """
    # 默认核心模块
    default_modules = [
        "auth",
        "billing",
        "repo",
        "quota",
        "api",
        "middleware",
        "database",
        "security",
    ]

    modules = modules or default_modules
    formatter = logging.Formatter(
        LogConfig.DEFAULT_FORMAT,
        datefmt=LogConfig.DATE_FORMAT
    )

    for module in modules:
        logger_name = f"api_platform.{module}"
        logger = logging.getLogger(logger_name)

        # 清除现有处理器
        logger.handlers.clear()

        # 设置级别
        level = LogConfig.LEVELS.get(root_level.upper(), logging.INFO)
        logger.setLevel(level)
        logger.propagate = False

        # 控制台处理器
        if enable_console:
            try:
                if sys.platform == 'win32':
                    console_handler = logging.StreamHandler(sys.stdout.buffer if hasattr(sys.stdout, 'buffer') else open(os.devnull, 'w'))
                else:
                    console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(level)
                console_handler.setFormatter(formatter)
                logger.addHandler(console_handler)
            except Exception:
                pass

        # 模块文件处理器
        if enable_file:
            module_handler = AutoBackupRotatingFileHandler(
                filename=str(MODULE_LOG_DIR / f"{module}.log"),
                maxBytes=LogBackupManager().get_max_size_bytes(),
                backupCount=LogConfig.BACKUP_COUNT,
                encoding="utf-8"
            )
            module_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
            module_handler.setFormatter(formatter)
            logger.addHandler(module_handler)


def setup_logger(
    name: str = "api_platform",
    level: str = None,
    log_file: str = None,
    enable_console: bool = True,
    enable_file: bool = True,
    file_rotation: str = "size",
    setup_modules: bool = True,
) -> logging.Logger:
    # 日志文件名加上日期和前缀
    date_str = datetime.now().strftime("%Y%m%d")
    # 文件名前缀
    file_prefix = "server"
    """
    设置日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径 (默认: logs/{name}.log)
        enable_console: 是否输出到控制台
        enable_file: 是否输出到文件
        file_rotation: 文件轮转方式 ("size" 按大小, "time" 按时间)
        setup_modules: 是否同时设置模块级日志记录器

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 获取日志记录器
    logger = logging.getLogger(name)

    # 清除现有处理器
    logger.handlers.clear()

    # 设置级别
    level = level or LogConfig.DEFAULT_LEVEL
    logger.setLevel(LogConfig.LEVELS.get(level.upper(), logging.INFO))

    # 格式化器
    formatter = logging.Formatter(
        LogConfig.DEFAULT_FORMAT,
        datefmt=LogConfig.DATE_FORMAT
    )
    colored_formatter = ColoredFormatter(
        LogConfig.DEFAULT_FORMAT,
        datefmt=LogConfig.DATE_FORMAT
    )

    # 控制台处理器
    if enable_console:
        try:
            # Windows 异步环境兼容：使用 NullHandler 作为后备
            if sys.platform == 'win32':
                console_handler = logging.StreamHandler(sys.stdout.buffer if hasattr(sys.stdout, 'buffer') else open(os.devnull, 'w'))
            else:
                console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(LogConfig.LEVELS.get(level.upper(), logging.INFO))
            console_handler.setFormatter(colored_formatter)
            logger.addHandler(console_handler)
        except Exception:
            pass

    # 文件处理器
    if enable_file:
        log_file = log_file or str(LOG_DIR / f"{file_prefix}_{name}_{date_str}.log")
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)

        if file_rotation == "time":
            file_handler = TimedRotatingFileHandler(
                filename=log_file,
                when=LogConfig.WHEN,
                interval=LogConfig.INTERVAL,
                backupCount=LogConfig.BACKUP_COUNT,
                encoding="utf-8"
            )
        else:
            file_handler = AutoBackupRotatingFileHandler(
                filename=log_file,
                maxBytes=LogBackupManager().get_max_size_bytes(),
                backupCount=LogConfig.BACKUP_COUNT,
                encoding="utf-8"
            )

        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 防止日志传播到根记录器
    logger.propagate = False

    # 设置模块级日志记录器
    if setup_modules:
        setup_module_loggers(
            root_level=level,
            enable_console=enable_console,
            enable_file=enable_file
        )

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称，格式: "module.submodule"

    Returns:
        logging.Logger: 日志记录器
    """
    if name:
        parent = logging.getLogger("api_platform")
        return parent.getChild(name)
    return logging.getLogger("api_platform")


# 全局备份管理器实例
backup_manager = LogBackupManager()

# 默认日志记录器
logger = setup_logger("api_platform")


# ==================== 日志文件操作函数 ====================

def get_log_files() -> List[Dict[str, Any]]:
    """获取所有日志文件信息"""
    files = []
    
    # 主日志文件 (带日期和前缀)
    today = datetime.now().strftime("%Y%m%d")
    main_log = LOG_DIR / f"server_api_platform_{today}.log"
    if main_log.exists():
        stat = main_log.stat()
        files.append({
            "name": f"server_api_platform_{today}.log",
            "path": str(main_log),
            "module": "main",
            "size": stat.st_size,
            "size_formatted": _format_size(stat.st_size),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    else:
        # 兼容旧文件名
        old_main_log = LOG_DIR / "api_platform.log"
        old_main_log_new = LOG_DIR / f"api_platform_{today}.log"
        if old_main_log.exists():
            stat = old_main_log.stat()
            files.append({
                "name": "api_platform.log",
                "path": str(old_main_log),
                "module": "main",
                "size": stat.st_size,
                "size_formatted": _format_size(stat.st_size),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
        elif old_main_log_new.exists():
            stat = old_main_log_new.stat()
            files.append({
                "name": f"api_platform_{today}.log",
                "path": str(old_main_log_new),
                "module": "main",
                "size": stat.st_size,
                "size_formatted": _format_size(stat.st_size),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
    
    # 模块日志文件
    for f in MODULE_LOG_DIR.glob("*.log"):
        stat = f.stat()
        files.append({
            "name": f.name,
            "path": str(f),
            "module": f.stem,
            "size": stat.st_size,
            "size_formatted": _format_size(stat.st_size),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    
    return sorted(files, key=lambda x: x["name"])


def read_log_content(
    file_path: str,
    start_line: int = 0,
    max_lines: int = 1000,
    level_filter: str = None,
    keyword: str = None,
) -> Dict[str, Any]:
    """
    读取日志文件内容

    Args:
        file_path: 日志文件路径
        start_line: 起始行号
        max_lines: 最大读取行数
        level_filter: 级别过滤 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        keyword: 关键词过滤

    Returns:
        包含lines和total的字典
    """
    path = Path(file_path)
    if not path.exists():
        return {"lines": [], "total": 0, "error": "文件不存在"}

    lines = []
    total_lines = 0

    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            total_lines = len(all_lines)

        # 过滤
        for i, line in enumerate(all_lines):
            # 级别过滤
            if level_filter:
                level_match = re.search(r'\|\s*(' + level_filter + r')\s*\|', line)
                if not level_match:
                    continue

            # 关键词过滤
            if keyword and keyword.lower() not in line.lower():
                continue

            # 分页
            if i < start_line:
                continue
            if len(lines) >= max_lines:
                break

            # 解析日志行
            parsed = _parse_log_line(line, i + 1)
            if parsed:
                lines.append(parsed)

    except Exception as e:
        return {"lines": [], "total": 0, "error": str(e)}

    return {
        "lines": lines,
        "total": total_lines,
        "start_line": start_line,
        "max_lines": max_lines,
    }


def _parse_log_line(line: str, line_number: int) -> Optional[Dict[str, Any]]:
    """解析单行日志"""
    stripped = line.strip()
    if not stripped:
        return None

    # 匹配实际格式: 2024-01-01 12:00:00 | [SERVER] | LEVEL     | module:line | message
    pattern = r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s*\|\s*\[SERVER\]\s*\|\s*(\w+)\s*\|\s*([^|]+):(\d+)\s*\|\s*(.*)$'
    match = re.match(pattern, stripped)

    if match:
        timestamp, level, module_info, line_num, message = match.groups()
        module_name = module_info.strip()
        return {
            "line_number": line_number,
            "timestamp": timestamp,
            "level": level,
            "module": module_name,
            "message": message.strip(),
            "raw": stripped,
            "color": LogConfig.LEVEL_COLORS.get(level, "#000000"),
        }

    # 尝试简化格式: timestamp | LEVEL | message (无module)
    simple_pattern = r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s*\|\s*(\w+)\s*\|\s*(.*)$'
    simple_match = re.match(simple_pattern, stripped)
    if simple_match:
        timestamp, level, message = simple_match.groups()
        return {
            "line_number": line_number,
            "timestamp": timestamp,
            "level": level,
            "module": "",
            "message": message.strip(),
            "raw": stripped,
            "color": LogConfig.LEVEL_COLORS.get(level, "#000000"),
        }

    # 其他格式 - 直接返回原行内容
    return {
        "line_number": line_number,
        "timestamp": "",
        "level": "INFO",
        "module": "",
        "message": stripped,
        "raw": stripped,
        "color": "#52c41a",
    }


def _format_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def get_log_stats() -> Dict[str, Any]:
    """获取日志统计信息"""
    files = get_log_files()
    backups = backup_manager.get_backup_files()

    total_size = sum(f["size"] for f in files)
    backup_size = sum(b["size"] for b in backups)

    return {
        "total_files": len(files),
        "total_size": total_size,
        "total_size_formatted": _format_size(total_size),
        "backup_count": len(backups),
        "backup_size": backup_size,
        "backup_size_formatted": _format_size(backup_size),
        "config": backup_manager.config,
    }


# ==================== 快捷日志函数 ====================

def log_debug(message: str, **kwargs):
    """记录调试信息"""
    logger.debug(message, **kwargs)


def log_info(message: str, **kwargs):
    """记录一般信息"""
    logger.info(message, **kwargs)


def log_warning(message: str, **kwargs):
    """记录警告信息"""
    logger.warning(message, **kwargs)


def log_error(message: str, **kwargs):
    """记录错误信息"""
    logger.error(message, **kwargs)


def log_critical(message: str, **kwargs):
    """记录严重错误"""
    logger.critical(message, **kwargs)


def log_exception(message: str, **kwargs):
    """记录异常信息 (包含堆栈)"""
    logger.exception(message, **kwargs)
