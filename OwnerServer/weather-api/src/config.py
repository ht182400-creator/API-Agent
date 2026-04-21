"""
Weather API 配置文件
负责管理应用配置和环境变量
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    app_name: str = "Weather API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # 服务器配置
    # 注意：8000 端口为 API 平台后端占用，Weather API 使用 8001
    host: str = "0.0.0.0"
    port: int = 8001
    
    # 天气数据源配置（可配置多个数据源）
    weather_api_url: str = "https://api.weather.gov.cn"
    weather_api_key: Optional[str] = None
    
    # 缓存配置
    cache_enabled: bool = True
    cache_ttl: int = 1800  # 缓存时间（秒），默认30分钟
    
    # 限流配置
    rate_limit_per_minute: int = 60
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/weather_api.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()
