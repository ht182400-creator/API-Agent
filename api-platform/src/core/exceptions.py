"""Custom exceptions - 自定义异常"""


class APIError(Exception):
    """Base API exception"""

    def __init__(
        self,
        message: str,
        code: int = 50001,
        details: dict = None,
        status_code: int = 500,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(APIError):
    """Authentication failed"""

    def __init__(self, message: str = "Authentication failed", code: int = 40101):
        super().__init__(message, code, status_code=401)


class InvalidAPIKeyError(AuthenticationError):
    """Invalid API Key"""

    def __init__(self):
        super().__init__("Invalid API Key", code=40102)


class APIKeyDisabledError(AuthenticationError):
    """API Key is disabled"""

    def __init__(self):
        super().__init__("API Key is disabled", code=40103)


class APIKeyExpiredError(AuthenticationError):
    """API Key has expired"""

    def __init__(self):
        super().__init__("API Key has expired", code=40104)


class InvalidSignatureError(AuthenticationError):
    """Invalid HMAC signature"""

    def __init__(self):
        super().__init__("Invalid signature", code=40002)


class TimestampExpiredError(AuthenticationError):
    """Request timestamp expired"""

    def __init__(self):
        super().__init__("Timestamp expired", code=40003)


class AuthorizationError(APIError):
    """Authorization failed"""

    def __init__(self, message: str = "Access denied", code: int = 40301):
        super().__init__(message, code, status_code=403)


class NotFoundError(APIError):
    """Resource not found"""

    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", code=40401, status_code=404)


class RepositoryNotFoundError(NotFoundError):
    """Repository not found"""

    def __init__(self):
        super().__init__("Repository")


class EndpointNotFoundError(NotFoundError):
    """Endpoint not found"""

    def __init__(self):
        super().__init__("Endpoint")


class RateLimitError(APIError):
    """Rate limit exceeded"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = 60,
        limit: int = 100,
    ):
        super().__init__(
            message,
            code=42901,
            details={"retry_after": retry_after, "limit": limit},
            status_code=429,
        )
        self.retry_after = retry_after


class QuotaExceededError(APIError):
    """Quota exceeded"""

    def __init__(
        self,
        message: str = "Quota exceeded",
        quota_type: str = "daily",
        used: int = 0,
        limit: int = 0,
    ):
        super().__init__(
            message,
            code=42902,
            details={"quota_type": quota_type, "used": used, "limit": limit},
            status_code=429,
        )


class ValidationError(APIError):
    """Validation error"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code=40001, details=details or {}, status_code=400)


class RepositoryUnavailableError(APIError):
    """Repository service unavailable"""

    def __init__(self, message: str = "Repository service unavailable"):
        super().__init__(message, code=50301, status_code=503)


class RepositoryTimeoutError(APIError):
    """Repository response timeout"""

    def __init__(self, timeout_ms: int = 30000):
        super().__init__(
            "Repository response timeout",
            code=50302,
            details={"timeout_ms": timeout_ms},
            status_code=504,
        )


class ExternalServiceError(APIError):
    """External service error"""

    def __init__(self, service: str, message: str = "External service error"):
        super().__init__(
            message, code=50001, details={"service": service}, status_code=502
        )
