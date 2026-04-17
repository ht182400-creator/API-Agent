"""Adapters module - 适配器模块"""

from .base import BaseAdapter, AdapterRequest, AdapterResponse
from .http_adapter import HTTPAdapter

__all__ = [
    "BaseAdapter",
    "AdapterRequest",
    "AdapterResponse",
    "HTTPAdapter",
]
