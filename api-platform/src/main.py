"""
Main application entry point - 通用API服务平台

This is the main entry point for the FastAPI application.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.config import settings
from src.config.database import init_db, close_db
from src.config.logging_config import setup_logger, get_logger
from src.core.middleware import setup_middleware
from src.core.exceptions import APIError
from src.api import api_router

# 初始化日志系统
setup_logger(
    name="api_platform",
    level=settings.log_level.upper(),
    enable_console=True,
    enable_file=True
)
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting API Platform...")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down API Platform...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="API Platform",
    description="通用API服务平台 - API聚合中转站",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# Setup middleware
setup_middleware(app)


# Exception handlers
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Handle custom API errors"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "request_id": getattr(request.state, "request_id", None),
            "details": exc.details,
        },
    )


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    # 记录错误日志
    logger.error(
        "Unhandled exception: %s - %s",
        request.url.path,
        str(exc)
    )
    logger.debug("Exception details: %s", exc)
    
    if settings.debug:
        import traceback
        return JSONResponse(
            status_code=500,
            content={
                "code": 50001,
                "message": str(exc),
                "request_id": getattr(request.state, "request_id", None),
                "details": {"traceback": traceback.format_exc()},
            },
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "code": 50001,
                "message": "Internal server error",
                "request_id": getattr(request.state, "request_id", None),
            },
        )


# Include API router
app.include_router(api_router, prefix=settings.api_v1_prefix)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.environment,
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "API Platform",
        "description": "通用API服务平台",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "disabled",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
