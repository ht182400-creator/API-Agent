"""Application settings - 应用设置"""

from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# 生产环境必须覆盖的默认（不安全）配置值
# 若生产环境仍使用这些值，启动时会被 validate_for_production() 拦截
INSECURE_DEFAULT_VALUES = {
    "jwt_secret_key": {
        "your-secret-key-change-in-production",
        "your-jwt-secret-key-change-in-production",
    },
    "secret_key": {
        "your-application-secret-key",
        "your-super-secret-key-change-in-production",
    },
    "api_key_encryption_secret": {
        "default-dev-secret-change-in-production",
    },
    "database_url": {
        "postgresql://api_user:password@localhost:5432/api_platform",
    },
    "redis_url": {
        "redis://:password@localhost:6379/0",
    },
}


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

    # Cache (缓存)
    cache_enabled: bool = True           # 缓存总开关（Redis 不可用时自动降级为不缓存）
    cache_default_ttl: int = 60          # 默认过期时间（秒）
    cache_key_prefix: str = "cache"      # 缓存 key 全局前缀

    # Readiness probe (就绪探针)
    # Redis 是否作为强依赖：默认 False（平台对 Redis 已做优雅降级，不应因 Redis 抖动摘除实例）
    ready_require_redis: bool = False

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

    # 限流后端：redis（推荐，分布式）/ database（回落旧逻辑）/ memory（单实例）
    rate_limit_backend: str = "redis"
    # Redis key 前缀
    rate_limit_redis_prefix: str = "rl"
    # 是否在中间件层按客户端 IP 限流
    # 注意：默认关闭，避免误伤前端 SPA 的高频并发请求；生产环境建议开启并调大阈值
    rate_limit_ip_enabled: bool = False
    # 单 IP 每分钟请求上限（仅在 rate_limit_ip_enabled=true 时生效）
    rate_limit_ip_per_minute: int = 600
    # 免限流路径（逗号分隔，前缀匹配）：健康检查、文档、支付回调等
    rate_limit_exempt_paths: str = (
        "/health,/ready,/docs,/redoc,/openapi.json,"
        "/api/v1/payments/alipay/callback"
    )

    # 仓库出站地址安全（SSRF 防护）
    # None = 自动：非生产环境允许私网/环回地址（便于本地示例 API 调试），
    #        生产环境自动禁止；
    # True = 始终允许私网地址（生产环境存在 SSRF 风险，谨慎使用）；
    # False = 始终禁止私网地址（最严格）。
    # 注意：云厂商元数据地址（169.254.169.254 等）在任何取值下都会被阻断。
    allow_private_repo_endpoints: Optional[bool] = None
    
    # Recharge Configuration (充值配置)
    recharge_min_amount: float = 1.0  # 最小充值金额
    recharge_max_amount: float = 10000.0  # 最大充值金额
    recharge_default_bonus_ratio: float = 0.0  # 默认赠送比例

    # Trial Configuration (试用配置)
    trial_amount: float = 20.0  # 试用金额（元）
    trial_enabled: bool = True  # 是否启用试用功能
    trial_one_time_only: bool = True  # 试用只能领取一次

    # Payment Configuration (支付配置)
    payment_mock_mode: bool = True  # 支付模拟模式开关，True=模拟支付，False=真实支付

    # 内部令牌：非生产环境下调用模拟支付回调(/payments/callback)时需携带 X-Internal-Token
    # 生产环境该接口直接下线（返回 404），不受此配置影响
    internal_api_token: str = ""

    # 支付回调来源 IP 白名单（逗号分隔的 IPv4/IPv6 地址或 CIDR 网段，如
    # "110.75.0.0/16,100.116.0.0/14"）。
    # 作用于 /payments/alipay/callback 与 /payments/callback：不在名单内的直连来源
    # 一律拒绝（403）。**未配置或为空 = 关闭校验**（保持既有部署行为不变）。
    # ⚠️ 安全决策只基于**直连 IP**（request.client.host），不使用 X-Forwarded-For
    #    （可伪造）。反代/负载均衡部署时，请将代理出口 IP 加入名单。
    payment_callback_ip_allowlist: str = ""

    # 分库护栏豁免：非生产环境**显式**允许连接生产库（危险，仅限确需的场景）
    # 默认 False —— 非生产环境若检测到 DATABASE_URL 指向疑似生产库，将拒绝启动
    allow_production_database: bool = False

    # Alipay Configuration (支付宝配置)
    alipay_sandbox: bool = True  # 是否使用沙箱环境
    alipay_app_id: str = ""  # 支付宝应用ID
    alipay_private_key: str = ""  # 应用私钥（RSA2 PKCS8格式）
    alipay_public_key: str = ""  # 支付宝公钥
    alipay_private_key_file: str = "keys/alipay_private_key_pkcs1.pem"  # 应用私钥文件路径（PKCS1格式）
    alipay_public_key_file: str = "keys/alipay_public_key.pem"  # 支付宝公钥文件路径
    alipay_notify_url: str = ""  # 异步通知地址
    alipay_return_url: str = ""  # 同步跳转地址
    alipay_sandbox_gateway: str = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"  # 沙箱网关地址
    alipay_production_gateway: str = "https://openapi.alipay.com/gateway.do"  # 生产网关地址
    
    # 前端配置 - 用于支付宝 return_url 跳转回前端页面
    # 使用 ngrok 等内网穿透时，前端无法直接被外网访问，需要配置此地址
    # 例如：https://abc123.ngrok.io（ngrok 映射的地址）
    #       或 http://your-domain.com（你的网站域名）
    frontend_base_url: str = "http://localhost:3000"  # 默认本地开发地址
    
    def get_alipay_private_key(self) -> str:
        """获取支付宝私钥，优先从文件读取"""
        import os
        if self.alipay_private_key:
            return self.alipay_private_key
        key_file = self.alipay_private_key_file
        if key_file and os.path.exists(key_file):
            with open(key_file, 'r') as f:
                return f.read()
        return ""
    
    def get_alipay_public_key(self) -> str:
        """获取支付宝公钥，优先从文件读取"""
        import os
        if self.alipay_public_key:
            return self.alipay_public_key
        key_file = self.alipay_public_key_file
        if key_file and os.path.exists(key_file):
            with open(key_file, 'r') as f:
                return f.read()
        return ""

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

    @field_validator("rate_limit_backend")
    @classmethod
    def validate_rate_limit_backend(cls, v: str) -> str:
        valid = ["redis", "database", "memory"]
        value = str(v).strip().lower()
        return value if value in valid else "redis"

    @property
    def rate_limit_exempt_path_list(self) -> List[str]:
        """免限流路径列表（前缀匹配）"""
        return [p.strip() for p in self.rate_limit_exempt_paths.split(",") if p.strip()]

    # ==================== 环境与生产安全校验 ====================

    @property
    def is_production(self) -> bool:
        """是否为生产环境（environment=production/prod）"""
        return str(self.environment).strip().lower() in ("production", "prod")

    @property
    def billing_environment(self) -> str:
        """
        账单/资金环境标识（唯一数据源）

        - 生产环境（environment=production/prod）→ "production"
        - 其余环境（development / staging / ...）→ "simulation"

        设计说明（与 payment_mock_mode 解耦）：
            "账单是否属于生产数据"应由**运行环境**决定，而不是"是否启用模拟支付"。
            否则在 development / staging 中联调真实（沙箱）支付时，
            本地产生的账单会被标记为 production，污染生产账单口径。

            因此两者职责分离：
                billing_environment  ← 由 ENVIRONMENT 决定（本属性）
                payment_mock_mode    ← 只决定"通用回调是否放行模拟"

        所有写入或过滤账单（bills / monthly_bills）environment 字段的地方，
        都应使用本属性，避免逻辑分散导致数据不一致。
        """
        return "production" if self.is_production else "simulation"

    @property
    def private_repo_endpoints_allowed(self) -> bool:
        """
        是否允许仓库后端地址指向私网 / 环回地址（SSRF 防护开关的实际取值）。

        - 未显式配置（None）→ 非生产环境允许，生产环境禁止
        - 显式配置 True/False → 以配置为准

        说明：无论本属性取值如何，云厂商元数据地址始终被阻断。
        """
        if self.allow_private_repo_endpoints is not None:
            return bool(self.allow_private_repo_endpoints)
        return not self.is_production

    def collect_production_warnings(self) -> List[str]:
        """收集生产环境的配置风险项（返回值非空即代表配置不安全）"""
        issues: List[str] = []
        if self.is_production:
            if self.payment_mock_mode:
                issues.append("PAYMENT_MOCK_MODE 仍为 true：生产环境必须关闭模拟支付")
            if self.alipay_sandbox:
                issues.append("ALIPAY_SANDBOX 仍为 true：生产环境必须使用正式网关")
            if self.debug:
                issues.append("DEBUG 仍为 true：生产环境建议关闭")
        for field, defaults in INSECURE_DEFAULT_VALUES.items():
            if getattr(self, field, None) in defaults:
                issues.append(f"{field.upper()} 仍为默认值，必须更换为安全值")
        return issues

    def validate_for_production(self) -> None:
        """
        生产环境启动前强校验（fail-fast）

        一旦检测到不安全配置，直接抛出异常中断启动，
        避免"带着测试配置上线"导致资金与数据风险。
        """
        if not self.is_production:
            return
        issues = (
            self.collect_production_warnings()
            + self.collect_database_separation_issues()
        )
        if issues:
            raise RuntimeError(
                "生产环境配置校验失败，拒绝启动：\n  - " + "\n  - ".join(issues)
            )

    # ==================== 分库护栏（环境 ↔ 数据库 一致性） ====================

    @property
    def database_name(self) -> str:
        """从 DATABASE_URL 中提取数据库名"""
        tail = str(self.database_url).rsplit("/", 1)[-1]
        return tail.split("?")[0].strip()

    def collect_database_separation_issues(self) -> List[str]:
        """
        检查「运行环境」与「数据库」是否匹配（**分库护栏**）。

        规则：
            - 生产环境：禁止连接疑似开发/测试库（库名含 dev / test / staging / local）
            - 非生产环境：禁止连接疑似生产库（库名含 prod）
              —— 这条最关键，用于防止本地开发/测试**误操作生产数据**

        说明：
            库名判定基于 `DATABASE_URL` 中的库名子串，属"尽力而为"的护栏；
            真正的隔离仍依赖各环境使用**独立的数据库实例**。
        """
        issues: List[str] = []
        db_name = self.database_name.lower()
        if not db_name:
            return issues

        _NON_PROD_HINTS = ("dev", "test", "staging", "local")

        if self.is_production:
            if any(hint in db_name for hint in _NON_PROD_HINTS):
                issues.append(
                    f"DATABASE_URL 指向疑似非生产库 '{db_name}'，"
                    f"生产环境（environment={self.environment}）禁止连接"
                )
        elif "prod" in db_name:
            issues.append(
                f"DATABASE_URL 指向疑似**生产库** '{db_name}'，"
                f"当前环境为 '{self.environment}'，已禁止连接以防误操作生产数据"
                f"（如确需连接，请显式设置 ALLOW_PRODUCTION_DATABASE=true）"
            )
        return issues

    def validate_database_separation(self) -> None:
        """
        分库护栏校验（**所有环境**启动时执行，fail-fast）。

        为什么需要：
            "生产与测试共用同一数据库、仅靠字段区分"是资金类系统的**高危形态** ——
            一次配置写错就可能在生产库上跑测试，或把测试数据写进生产库。
            **分库 + 启动校验**可从机制上避免此类事故。

        豁免：非生产环境可通过 ``ALLOW_PRODUCTION_DATABASE=true`` 显式放行；
             生产环境的库名问题并入 ``validate_for_production()`` 统一报错。
        """
        if self.is_production:
            return  # 生产侧由 validate_for_production() 统一校验
        if self.allow_production_database:
            return

        issues = self.collect_database_separation_issues()
        if issues:
            raise RuntimeError(
                "数据库与环境不匹配，拒绝启动：\n  - " + "\n  - ".join(issues)
            )

    def collect_security_notices(self) -> List[str]:
        """
        收集非致命的安全提示（仅告警，不阻断启动）

        与 collect_production_warnings() 的区别：本方法返回的是"已显式做出
        取舍但仍有风险"的项，需要运维知悉，但不应阻断服务启动。
        """
        notices: List[str] = []
        if self.is_production and self.allow_private_repo_endpoints is True:
            notices.append(
                "ALLOW_PRIVATE_REPO_ENDPOINTS=true：生产环境允许仓库指向内网地址，"
                "存在 SSRF 风险（云元数据地址仍会被阻断）"
            )
        return notices


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
