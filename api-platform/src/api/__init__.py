"""API module - API路由

路由注册约定（重要）：
    所有 v1 子路由都必须在 `src/api/v1/__init__.py` 中集中注册，并通过
    `v1_router` 统一挂载到 `settings.api_v1_prefix`（默认 /api/v1）之下。

    本文件**只负责挂载 v1_router**，不要再在此处重复 include 任何子路由，
    否则会出现两类问题：
      1. 同一路由被注册两次（路径重复、OpenAPI 文档重复）；
      2. 子路由以"无前缀"形式被意外暴露，例如
         admin_logs 会同时出现在 /api/v1/logs/*（未加 /admin 前缀），
         造成路径与预期不符甚至越权访问面扩大。

历史问题（已修复）：
    本文件曾额外 include `admin_logs_router` 与 `analytics_router`，
    导致上述重复注册与无前缀暴露。
"""

from fastapi import APIRouter

from .v1 import api_router as v1_router

api_router = APIRouter()
api_router.include_router(v1_router, tags=["v1"])

__all__ = ["api_router"]
