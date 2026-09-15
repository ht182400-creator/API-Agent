"""
Main application entry point - 通用API服务平台

This is the main entry point for the FastAPI application.
"""

import logging
from contextlib import asynccontextmanager

# 禁用 uvicorn 和 starlette 的日志，避免 Windows multiprocessing 子进程 stdout 关闭问题
for logger_name in [
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "uvicorn.asgi",
    "starlette",
    "starlette.access",
    "uvicorn.protocols.http",
    "uvicorn.protocols",
    "uvicorn.main",
    "uvicorn.lifespan",
]:
    logging.getLogger(logger_name).disabled = True

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.config import settings
from src.config.database import init_db, close_db
from src.config.logging_config import setup_logger, get_logger, error_logger
from src.core.middleware import setup_middleware
from src.core.exceptions import APIError
from src.api import api_router

# 初始化日志系统
# 注意: 禁用控制台日志以避免 Windows multiprocessing 子进程的 stdout 关闭问题
# 错误日志会记录到 logs/errors.log
setup_logger(
    name="api_platform",
    level=settings.log_level.upper(),
    enable_console=False,  # 禁用控制台输出
    enable_file=True
)
logger = get_logger("main")


def _print_environment_banner() -> None:
    """
    打印启动环境横幅（L4「明显提示」）。

    为什么直接 print 而不用 logger：
        本项目日志系统启用了 ``enable_console=False``（用于规避 Windows
        multiprocessing 子进程 stdout 被关闭的问题），因此 logger 只写文件、
        终端看不到。为了让开发者/运维"启动第一眼就知道当前是什么环境"，
        这里直接写 stdout。

    注意：只使用 ``print``，**不要**包装 ``sys.stdout``
          （包装会在 GC 时关闭真实 stdout，导致 pytest/uvicorn 崩溃）。
    """
    width = 64
    border = "=" * width

    if settings.is_production:
        marker = "!!! PRODUCTION !!!  生产环境 —— 真实资金流转，请谨慎操作"
    else:
        marker = f"非生产环境 [{settings.environment.upper()}] —— 可自由测试"

    print("\n" + border)
    print(f"  {marker}")
    print(
        f"  账单环境: {settings.billing_environment}"
        f" | 模拟支付: {'开启' if settings.payment_mock_mode else '关闭'}"
        f" | 支付宝沙箱: {'是' if settings.alipay_sandbox else '否'}"
    )
    print(
        f"  调试模式: {'开启' if settings.debug else '关闭'}"
        f" | 日志级别: {settings.log_level.upper()}"
    )
    print(border + "\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting API Platform...")

    # 【L4】启动环境横幅（终端可见，避免在错误环境上误操作）
    _print_environment_banner()

    # 环境信息与生产安全强校验（fail-fast）
    logger.info(
        "Environment=%s | BillingEnvironment=%s | MockPayment=%s | AlipaySandbox=%s",
        settings.environment,
        settings.billing_environment,
        settings.payment_mock_mode,
        settings.alipay_sandbox,
    )
    warnings = settings.collect_production_warnings()
    if warnings:
        # 非生产环境仅告警；生产环境由 validate_for_production() 直接中断启动
        logger.warning("配置风险项(%s)：\n  - %s", settings.environment, "\n  - ".join(warnings))
    settings.validate_for_production()

    # 【分库护栏】所有环境都校验"环境 ↔ 数据库"是否匹配：
    # 非生产环境若指向疑似生产库，直接拒绝启动（防误操作生产数据）
    settings.validate_database_separation()

    # 非致命安全提示（不阻断启动）
    notices = settings.collect_security_notices()
    if notices:
        logger.warning("安全提示：\n  - %s", "\n  - ".join(notices))

    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down API Platform...")
    await close_db()
    logger.info("Database connections closed")

    from src.core.redis_manager import close_redis
    await close_redis()


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
    # 使用专用错误日志记录器
    error_logger.error(
        "Unhandled exception on %s: %s",
        request.url.path,
        str(exc),
        exc_info=True
    )
    
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
    """
    Health check endpoint（存活探针：仅表明进程在运行）

    同时对外暴露当前环境标识，供前端展示环境徽标 / 脚本自检使用。
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        # 运行环境（development / staging / production）
        "environment": settings.environment,
        # 账单环境（simulation / production）—— 前端据此显示环境徽标
        "billing_environment": settings.billing_environment,
        "is_production": settings.is_production,
        "payment_mock_mode": settings.payment_mock_mode,
    }


@app.get("/ready")
async def readiness_check():
    """
    就绪探针（Readiness Probe）

    校验关键依赖是否可用，用于容器编排判断是否将实例接入流量：
    - 全部就绪 → 200
    - 必需依赖不可用 → 503

    依赖策略：
        database —— **必需**（不可用则不就绪）
        redis    —— 默认**非必需**（平台对 Redis 已做优雅降级：
                    限流回落数据库计数、缓存自动跳过），
                    可通过 READY_REQUIRE_REDIS=true 改为强依赖。
    """
    from sqlalchemy import text

    from src.config.database import async_engine
    from src.core.redis_manager import RedisManager

    checks: dict = {}
    ready = True

    # 数据库（必需）
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = {"status": "up", "required": True}
    except Exception as exc:
        checks["database"] = {
            "status": "down",
            "required": True,
            "error": str(exc)[:200],
        }
        ready = False

    # Redis（默认非必需）
    redis_up = await RedisManager.is_available()
    checks["redis"] = {"status": "up" if redis_up else "down", "required": settings.ready_require_redis}
    if settings.ready_require_redis and not redis_up:
        ready = False

    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "not_ready",
            "version": "1.0.0",
            "environment": settings.environment,
            "checks": checks,
        },
    )


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
    import logging
    
    # 完全禁用 uvicorn 的日志，避免 Windows multiprocessing 子进程刷屏
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "uvicorn.asgi"]:
        logging.getLogger(logger_name).disabled = True
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="warning",  # 只显示 warning 及以上的日志
        access_log=False,
    )
