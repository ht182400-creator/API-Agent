"""Configuration module - 应用配置"""

from .settings import settings

# Lazy imports to avoid initialization during testing
def __getattr__(name):
    if name in ["get_db", "engine", "AsyncSessionLocal", "async_engine"]:
        from . import database
        return getattr(database, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["settings"]
