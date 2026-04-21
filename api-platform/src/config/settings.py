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
    cors_origins: str = "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000,http://127.0.0.1:8080"
    cors_allow_all_localhost: bool = True  # 开发模式：允许所有 localhost 端口

    @property
    def cors_origins_list(self) -> List[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",")]
        if self.cors_allow_all_localhost and self.environment == "development":
            # 开发模式下自动添加 localhost:3000-9999
            for port in range(3000, 10000):
                origins.extend([
                    f"http://localhost:{port}",
                    f"http://127.0.0.1:{port}",
                ])
        return list(set(origins))  # 去重

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 100
    
    # Recharge Configuration (充值配置)
    recharge_min_amount: float = 1.0  # 最小充值金额
    recharge_max_amount: float = 10000.0  # 最大充值金额
    recharge_default_bonus_ratio: float = 0.0  # 默认赠送比例

    # Payment Configuration (支付配置)
    payment_mock_mode: bool = True  # 支付模拟模式开关，True=模拟支付，False=真实支付

    # ==================== 计费配置 ====================
    # 默认计费规则（当仓库没有配置 RepoPricing 时使用）
    billing_default_enabled: bool = True  # 是否启用默认计费
    billing_default_type: str = "per_call"  # 计费类型: per_call, token, free
    billing_default_price_per_call: float = 0.01  # 按次计费单价（元）
    billing_default_price_per_token: float = 0.0001  # 按Token计费单价（元/Token）
    billing_default_free_calls: int = 0  # 免费调用次数（每个API Key）
    billing_default_free_tokens: int = 0  # 免费Token数（每个API Key）

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
