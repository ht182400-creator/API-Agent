"""Middleware - 中间件"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.config.logging_config import get_logger

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
    """Middleware for rate limiting"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Rate limiting logic would be implemented here
        # For now, pass through
        response = await call_next(request)
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
    )

    # Request Logging Middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Rate Limiting Middleware
    app.add_middleware(RateLimitMiddleware)
