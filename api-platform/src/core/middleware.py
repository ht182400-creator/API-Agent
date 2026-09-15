"""Middleware - 中间件"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.config.logging_config import get_logger
from src.core.rate_limiter import check_rate_limit
from src.utils.helpers import get_client_ip

# 模块日志记录器
logger = get_logger("middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Add request ID to response headers
        start_time = time.time()

        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Log request details
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        # 使用日志系统记录
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(process_time * 1000, 2),
            "client_ip": request.client.host if request.client else "unknown",
        }

        if response.status_code >= 500:
            logger.error("[SRV-API] Request completed with error: %s", log_data)
        elif response.status_code >= 400:
            logger.warning("[SRV-API] Request completed with warning: %s", log_data)
        else:
            logger.info("[SRV-API] Request completed: %s %s -> %s (%.2fms)",
                request.method, request.url.path, response.status_code, process_time * 1000)

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    按客户端 IP 的限流中间件

    说明（评审项 P0-3）：
        - 改造前本中间件为空实现，真正的限流逻辑（API Key 维度）在
          AuthService._check_rate_limit 中通过查询数据库计数实现，高并发下会拖垮数据库。
        - 现由 Redis 承担计数（src/core/rate_limiter.py），Redis 不可用时自动降级为
          进程内内存计数，保证不出现"完全无限流"。
        - 本中间件负责 **IP 维度** 的兜底限流（防刷），默认关闭
          （RATE_LIMIT_IP_ENABLED），避免误伤前端 SPA 的高频并发请求。

    注意：
        中间件位于 FastAPI 异常处理器之外，因此这里必须直接返回 JSONResponse，
        不能抛出 APIError（否则会变成 500）。
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 总开关 / IP 维度开关
        if not settings.rate_limit_enabled or not settings.rate_limit_ip_enabled:
            return await call_next(request)

        path = request.url.path

        # 免限流路径（前缀匹配）：健康检查、文档、支付回调等
        for exempt in settings.rate_limit_exempt_path_list:
            if path.startswith(exempt):
                return await call_next(request)

        client_ip = get_client_ip(request) or (request.client.host if request.client else "unknown")

        result = await check_rate_limit(
            scope="ip",
            identifier=client_ip,
            limit=settings.rate_limit_ip_per_minute,
            window_seconds=60,
            prefix=settings.rate_limit_redis_prefix,
        )

        if not result.allowed:
            logger.warning(
                "[RateLimit] IP 限流触发: ip=%s path=%s current=%s/%s backend=%s",
                client_ip,
                path,
                result.current,
                result.limit,
                result.backend,
            )
            headers = {**result.to_headers(), "Retry-After": str(result.reset_after)}
            return JSONResponse(
                status_code=429,
                headers=headers,
                content={
                    "code": 42901,
                    "message": "请求过于频繁，请稍后再试",
                    "request_id": getattr(request.state, "request_id", None),
                    "details": {
                        "scope": "ip",
                        "limit": result.limit,
                        "window_seconds": 60,
                        "retry_after": result.reset_after,
                    },
                },
            )

        response = await call_next(request)

        # 附加限流信息响应头（便于客户端与 SDK 自适应）
        for key, value in result.to_headers().items():
            response.headers.setdefault(key, value)

        return response


class EnvironmentHeaderMiddleware(BaseHTTPMiddleware):
    """
    环境标识响应头中间件。

    为每个响应附加当前运行环境，便于：
      - 前端 / SDK / 脚本在不解析响应体的情况下判断所处环境；
      - 排障时快速确认请求落到了哪个环境。

    头信息：
        X-Environment         —— 运行环境（development / staging / production）
        X-Billing-Environment —— 账单环境（simulation / production）

    注意：跨域场景下前端 JS 需读取这些头时，须在 CORS 中 expose_headers 声明
          （已在 setup_middleware 中配置）。
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Environment", settings.environment)
        response.headers.setdefault("X-Billing-Environment", settings.billing_environment)
        return response


def setup_middleware(app):
    """Setup all middleware for the application"""
    from src.config.settings import settings

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # 允许前端 JS 读取自定义头（跨域时默认不暴露）
        expose_headers=[
            "X-Request-ID",
            "X-Process-Time",
            "X-Environment",
            "X-Billing-Environment",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
        ],
    )

    # Request Logging Middleware
    app.add_middleware(RequestLoggingMiddleware)

    # 环境标识响应头（供前端/脚本感知当前环境）
    app.add_middleware(EnvironmentHeaderMiddleware)

    # Rate Limiting Middleware
    app.add_middleware(RateLimitMiddleware)
