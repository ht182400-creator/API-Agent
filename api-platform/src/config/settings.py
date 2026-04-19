"""Application settings - 应用设置"""

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API Configuration
    api_v1_prefix: str = "/api/v1"
    debug: bool = True
    log_level: str = "debug"
    environment: str = "development"

    # Database Configuration
    database_url: str = "postgresql://api_user:password@localhost:5432/api_platform"
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Redis Configuration
    redis_url: str = "redis://:password@localhost:6379/0"
    redis_max_connections: int = 50

    # JWT Configuration
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CORS Configuration
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 100

    # Security
    secret_key: str = "your-application-secret-key"
    encryption_key: str = "your-encryption-key-32-bytes"
    
    # API Key 加密密钥 (用于查看 API Key 明文功能)
    api_key_encryption_secret: str = "default-dev-secret-change-in-production"
    
    # Password Hashing Configuration
    # Supported modes: "bcrypt" (recommended), "sha256", "auto" (supports both)
    password_hash_mode: str = "auto"
    
    @field_validator("password_hash_mode")
    @classmethod
    def validate_hash_mode(cls, v: str) -> str:
        valid_modes = ["bcrypt", "sha256", "auto"]
        if v.lower() not in valid_modes:
            return "auto"
        return v.lower()
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["debug", "info", "warning", "error", "critical"]
        if v.lower() not in valid_levels:
            return "info"
        return v.lower()


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
