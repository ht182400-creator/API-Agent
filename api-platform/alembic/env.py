"""Alembic 迁移环境 —— 统一表结构变更来源（P1-8）

规则（重要）：
    1. 模型（src/models/*.py）是**唯一 schema 权威源**；
    2. 表结构变更一律走 ``alembic revision --autogenerate`` → 人工审查 → ``alembic upgrade head``；
    3. **禁止**再手写散装迁移脚本（历史上的 migrations/add_*.py 等已归档至
       scripts/legacy_migrations/，仅作历史记录）；
    4. 已存在的存量库首次接入时执行 ``alembic stamp head``（标记基线，不重复建表）。

连接来源（优先级）：
    1. ``alembic -x url=<DATABASE_URL>`` 命令行覆盖（用于临时库/跨库操作）；
    2. ``settings.database_url``（.env 的 DATABASE_URL，asyncpg → psycopg2 同步驱动转换）。
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# ---------------------------------------------------------------------------
# 连接串：-x url= 覆盖 > settings.database_url（同步化）
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

# 保证 alembic 从项目根（api-platform/）可 import src.*
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.settings import settings  # noqa: E402

_sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://").replace(
    "postgresql://", "postgresql+psycopg2://"
)

cmdline_url = context.get_x_argument(as_dictionary=True).get("url")
if cmdline_url:
    _sync_url = cmdline_url

config.set_main_option("sqlalchemy.url", _sync_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# 模型元数据：显式注册全部模型（models/__init__ 聚合），autogenerate 的对比基准
# ---------------------------------------------------------------------------
import src.models  # noqa: E402,F401  确保全部模型注册到 Base.metadata
from src.config.database import Base  # noqa: E402

target_metadata = Base.metadata

# autogenerate 忽略清单（非模型管理的对象）
_IGNORE_TABLES = {"alembic_version"}


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and name in _IGNORE_TABLES:
        return False
    return True


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
