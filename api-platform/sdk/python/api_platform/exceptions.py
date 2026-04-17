"""
API Platform Python SDK - 异常类型定义
"""

from typing import Optional, Dict, Any


class APIError(Exception):
    """
    API基础异常类
    
    Attributes:
        message: 错误消息
        code: 错误码
        request_id: 请求ID
        details: 错误详情
    """
    
    def __init__(
        self,
        message: str,
        code: int = -1,
        request_id: str = "",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.request_id = request_id
        self.details = details or {}
    
    def __repr__(self):
        return f"<{self.__class__.__name__} code={self.code} message='{self.message}'>"
    
    def __str__(self):
        return f"[{self.code}] {self.message}"


class AuthenticationError(APIError):
    """
    认证失败异常（401）
    
    可能的原因：
    - API Key无效
    - API Key已禁用
    - API Key已过期
    """
    pass


class RateLimitError(APIError):
    """
    限流错误异常（429）
    
    Attributes:
        limit_type: 限制类型（rpm/rph/daily/monthly）
        limit: 限制值
        remaining: 剩余配额
        retry_after: 重试等待时间（秒）
    """
    
    def __init__(
        self,
        message: str,
        code: int = 42901,
        request_id: str = "",
        limit_type: str = "rpm",
        limit: int = 0,
        remaining: int = 0,
        retry_after: int = 60,
        **kwargs
    ):
        super().__init__(message, code, request_id)
        self.limit_type = limit_type
        self.limit = limit
        self.remaining = remaining
        self.retry_after = retry_after


class QuotaExceededError(APIError):
    """
    配额超限异常
    
    可能的原因：
    - 月度配额已用完
    - 套餐额度已用完
    """
    
    def __init__(
        self,
        message: str,
        code: int = 42902,
        request_id: str = "",
        quota_type: str = "",
        used: float = 0,
        limit: float = 0,
        **kwargs
    ):
        super().__init__(message, code, request_id)
        self.quota_type = quota_type
        self.used = used
        self.limit = limit


class ValidationError(APIError):
    """
    参数验证错误异常（400）
    
    可能的原因：
    - 必填参数缺失
    - 参数格式错误
    - 参数值超出范围
    """
    
    def __init__(
        self,
        message: str,
        code: int = 40001,
        request_id: str = "",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, code, request_id, details)


class NotFoundError(APIError):
    """
    资源不存在异常（404）
    
    可能的原因：
    - 仓库不存在
    - 接口不存在
    - 资源已被删除
    """
    
    def __init__(
        self,
        message: str,
        code: int = 40401,
        request_id: str = "",
        resource_type: str = "",
        resource_id: str = "",
        **kwargs
    ):
        super().__init__(message, code, request_id)
        self.resource_type = resource_type
        self.resource_id = resource_id


class ServerError(APIError):
    """
    服务器错误异常（500/503）
    
    可能的原因：
    - 服务器内部错误
    - 仓库服务不可用
    - 仓库响应超时
    """
    pass


class NetworkError(APIError):
    """
    网络连接错误异常
    
    可能的原因：
    - 网络不可达
    - DNS解析失败
    - 连接被拒绝
    """
    
    def __init__(
        self,
        message: str,
        code: int = -1,
        request_id: str = "",
        cause: Optional[Exception] = None
    ):
        super().__init__(message, code, request_id)
        self.cause = cause


class TimeoutError(APIError):
    """
    请求超时异常
    
    可能的原因：
    - 服务器响应超时
    - 服务器处理时间过长
    """
    
    def __init__(
        self,
        message: str = "请求超时",
        code: int = -1,
        request_id: str = "",
        timeout: int = 30
    ):
        super().__init__(message, code, request_id)
        self.timeout = timeout


class RetryExhaustedError(APIError):
    """
    重试次数耗尽异常
    
    当所有重试次数用尽后仍然失败时抛出
    """
    
    def __init__(
        self,
        message: str = "重试次数耗尽",
        last_exception: Optional[Exception] = None
    ):
        super().__init__(message, code=-1)
        self.last_exception = last_exception
    
    def __str__(self):
        if self.last_exception:
            return f"{self.message}: {self.last_exception}"
        return self.message
