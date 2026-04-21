"""
Weather API 主入口文件
FastAPI 应用启动配置
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import sys

from .config import settings
from .endpoints import weather

# 配置日志输出到控制台
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level
)

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
## Weather API

天气 API 产品，提供以下功能：

- **实时天气查询** - 获取当前城市天气数据
- **天气预报查询** - 获取未来7天天气预报
- **空气质量查询** - 获取 AQI 及污染物数据
- **天气预警查询** - 获取灾害天气预警

## 认证方式

所有接口需要通过 API Key 进行认证：

```
Authorization: Bearer {API_KEY}
```
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"全局异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "error": {
                "code": "INTERNAL_ERROR",
                "details": str(exc)
            }
        }
    )


# 注册路由
app.include_router(weather.router, prefix="/api/v1")


@app.get("/", tags=["首页"])
async def root():
    """API 首页"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["健康检查"])
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "version": settings.app_version
    }


def main():
    """启动应用"""
    import uvicorn
    logger.info(f"启动 {settings.app_name} v{settings.app_version}，端口: {settings.port}")
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
