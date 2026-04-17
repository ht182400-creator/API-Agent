"""
API Platform Python SDK - 客户端主类
"""

import time
import hashlib
import hmac
import json
import logging
from typing import Optional, Dict, Any, Union
from urllib.parse import urljoin

import requests

from .exceptions import (
    APIError,
    AuthenticationError,
    RateLimitError,
    QuotaExceededError,
    ValidationError,
    NotFoundError,
    ServerError,
    NetworkError,
    TimeoutError,
    RetryExhaustedError
)
from .http_client import HTTPClient

logger = logging.getLogger(__name__)


class Client:
    """
    API Platform 同步客户端
    
    Attributes:
        api_key: API密钥
        api_secret: API密钥私钥（用于HMAC签名）
        base_url: API基础URL
        timeout: 请求超时时间（秒）
        max_retries: 最大重试次数
        retry_delay: 初始重试延迟（秒）
        retry_multiplier: 重试延迟倍数（指数退避）
        log_level: 日志级别
    """
    
    def __init__(
        self,
        api_key: str,
        api_secret: Optional[str] = None,
        base_url: str = "https://api.platform.com/v1",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        retry_multiplier: float = 2.0,
        log_level: str = "INFO"
    ):
        """
        初始化客户端
        
        Args:
            api_key: API密钥
            api_secret: API密钥私钥（可选，用于HMAC签名）
            base_url: API基础URL
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 初始重试延迟（秒）
            retry_multiplier: 重试延迟倍数
            log_level: 日志级别
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_multiplier = retry_multiplier
        
        # 配置日志
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        # HTTP客户端
        self._http = HTTPClient(
            base_url=self.base_url,
            timeout=timeout
        )
        
        # 仓库访问器
        self._repos = RepoAccessor(self)
    
    @property
    def psychology(self):
        """心理问答仓库"""
        return self._repos
    
    def _generate_signature(
        self,
        method: str,
        path: str,
        timestamp: str,
        nonce: str,
        body: str = ""
    ) -> str:
        """
        生成HMAC签名
        
        Args:
            method: HTTP方法
            path: 请求路径
            timestamp: 时间戳
            nonce: 随机字符串
            body: 请求体
            
        Returns:
            HMAC签名
        """
        if not self.api_secret:
            return ""
        
        string_to_sign = "\n".join([
            f"AccessKey={self.api_key}",
            f"Timestamp={timestamp}",
            f"Nonce={nonce}",
            f"BodyHash={hashlib.sha256(body.encode()).hexdigest()}"
        ])
        
        signature = hmac.new(
            self.api_secret.encode(),
            string_to_sign.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _make_headers(
        self,
        method: str,
        path: str,
        body: str = ""
    ) -> Dict[str, str]:
        """
        生成请求头
        
        Args:
            method: HTTP方法
            path: 请求路径
            body: 请求体
            
        Returns:
            请求头字典
        """
        timestamp = str(int(time.time() * 1000))
        nonce = hashlib.md5(f"{timestamp}:{self.api_key}".encode()).hexdigest()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-Api-Key": self.api_key,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce
        }
        
        # 如果提供了secret，添加HMAC签名
        if self.api_secret:
            signature = self._generate_signature(method, path, timestamp, nonce, body)
            headers["X-Signature"] = signature
        
        return headers
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        处理响应
        
        Args:
            response: requests响应对象
            
        Returns:
            响应数据
            
        Raises:
            APIError: API错误
        """
        status_code = response.status_code
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = {"message": response.text}
        
        error_code = data.get("code", 0)
        error_msg = data.get("message", "")
        request_id = data.get("request_id", "")
        
        if status_code == 200:
            return data
        
        # 构建错误对象
        error_kwargs = {
            "message": error_msg,
            "code": error_code,
            "request_id": request_id
        }
        
        if status_code == 401:
            raise AuthenticationError(**error_kwargs)
        elif status_code == 429:
            raise RateLimitError(
                message=error_msg,
                code=error_code,
                request_id=request_id,
                limit_type=data.get("limit_type", "rpm"),
                limit=data.get("limit", 0),
                remaining=data.get("remaining", 0),
                retry_after=data.get("retry_after", 60)
            )
        elif status_code == 403:
            raise APIError(**error_kwargs)
        elif status_code == 404:
            raise NotFoundError(**error_kwargs)
        elif status_code == 400:
            raise ValidationError(
                message=error_msg,
                code=error_code,
                request_id=request_id,
                details=data.get("details", {})
            )
        elif status_code >= 500:
            raise ServerError(
                message=error_msg,
                code=error_code,
                request_id=request_id
            )
        else:
            raise APIError(**error_kwargs)
    
    def _request_with_retry(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        带重试的请求
        
        Args:
            method: HTTP方法
            path: 请求路径
            params: URL参数
            json_data: JSON请求体
            **kwargs: 其他参数
            
        Returns:
            响应数据
            
        Raises:
            RetryExhaustedError: 重试次数耗尽
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                body = json.dumps(json_data) if json_data else ""
                headers = self._make_headers(method, path, body)
                
                response = self._http.request(
                    method=method,
                    path=path,
                    params=params,
                    json=json_data,
                    headers=headers,
                    **kwargs
                )
                
                return self._handle_response(response)
                
            except (RateLimitError, ServerError, NetworkError) as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    # 计算重试延迟
                    if isinstance(e, RateLimitError) and e.retry_after:
                        delay = e.retry_after
                    else:
                        delay = self.retry_delay * (self.retry_multiplier ** attempt)
                    
                    logger.warning(
                        f"请求失败（第{attempt + 1}次尝试），"
                        f"等待{delay:.1f}秒后重试：{e.message}"
                    )
                    time.sleep(min(delay, 60))  # 最多等待60秒
                else:
                    logger.error(f"重试次数耗尽，最后错误：{e}")
        
        raise RetryExhaustedError(
            f"重试{self.max_retries}次后仍然失败",
            last_exception=last_exception
        )
    
    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发起API请求
        
        Args:
            method: HTTP方法
            path: 请求路径
            params: URL参数
            json_data: JSON请求体
            **kwargs: 其他参数
            
        Returns:
            响应数据
        """
        return self._request_with_retry(
            method=method,
            path=path,
            params=params,
            json_data=json_data,
            **kwargs
        )
    
    def get(self, path: str, params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """GET请求"""
        return self.request("GET", path, params=params, **kwargs)
    
    def post(self, path: str, json_data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """POST请求"""
        return self.request("POST", path, json_data=json_data, **kwargs)
    
    def put(self, path: str, json_data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """PUT请求"""
        return self.request("PUT", path, json_data=json_data, **kwargs)
    
    def delete(self, path: str, **kwargs) -> Dict[str, Any]:
        """DELETE请求"""
        return self.request("DELETE", path, **kwargs)


class RepoAccessor:
    """
    仓库访问器
    提供动态访问各个API仓库的接口
    """
    
    def __init__(self, client: Client):
        self._client = client
        self._cache = {}
    
    def __getattr__(self, name: str):
        """动态获取仓库"""
        if name.startswith("_"):
            raise AttributeError(name)
        
        if name not in self._cache:
            self._cache[name] = Repo(self._client, name)
        
        return self._cache[name]


class Repo:
    """
    API仓库封装
    提供对特定仓库API的便捷访问
    """
    
    def __init__(self, client: Client, repo_name: str):
        self._client = client
        self._repo_name = repo_name
    
    def chat(self, message: str, **kwargs) -> 'ChatResponse':
        """
        心理问答聊天接口
        
        Args:
            message: 用户消息
            **kwargs: 其他参数（user_id, context等）
            
        Returns:
            ChatResponse对象
        """
        data = self._client.post(
            f"/repos/{self._repo_name}/chat",
            json_data={"message": message, **kwargs}
        )
        return ChatResponse(data)
    
    def call(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        通用API调用
        
        Args:
            endpoint: 端点名称
            **kwargs: 请求参数
            
        Returns:
            响应数据
        """
        return self._client.post(
            f"/repos/{self._repo_name}/{endpoint}",
            json_data=kwargs
        )
    
    def __getattr__(self, name: str):
        """动态获取端点"""
        if name.startswith("_"):
            raise AttributeError(name)
        
        def endpoint_call(**kwargs):
            return self.call(name, **kwargs)
        
        return endpoint_call


class ChatResponse:
    """
    心理问答响应
    """
    
    def __init__(self, data: Dict[str, Any]):
        self.answer = data.get("answer", "")
        self.suggestions = data.get("suggestions", [])
        self.request_id = data.get("request_id", "")
        self.usage = Usage(data.get("usage", {}))
        self._data = data
    
    def __repr__(self):
        return f"<ChatResponse answer='{self.answer[:50]}...' request_id='{self.request_id}'>"
    
    def __getitem__(self, key):
        return self._data.get(key)


class Usage:
    """
    用量信息
    """
    
    def __init__(self, data: Dict[str, Any]):
        self.tokens = data.get("tokens", 0)
        self.cost = data.get("cost", 0.0)
        self._data = data
    
    def __repr__(self):
        return f"<Usage tokens={self.tokens} cost={self.cost}>"


# 异步客户端
class AsyncClient:
    """
    API Platform 异步客户端
    """
    
    def __init__(
        self,
        api_key: str,
        api_secret: Optional[str] = None,
        base_url: str = "https://api.platform.com/v1",
        timeout: int = 30,
        max_retries: int = 3,
        log_level: str = "INFO"
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    async def _make_request(self, method: str, path: str, **kwargs):
        """异步请求（需要aiohttp支持）"""
        import asyncio
        try:
            import aiohttp
        except ImportError:
            raise ImportError(
                "请安装aiohttp: pip install aiohttp"
            )
        
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.api_key}"
        headers["X-Api-Key"] = self.api_key
        
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                **kwargs
            ) as response:
                data = await response.json()
                
                if response.status != 200:
                    raise APIError(
                        message=data.get("message", ""),
                        code=data.get("code", response.status),
                        request_id=data.get("request_id", "")
                    )
                
                return data
    
    async def post(self, path: str, **kwargs):
        """POST请求"""
        return await self._make_request("POST", path, **kwargs)
    
    async def get(self, path: str, **kwargs):
        """GET请求"""
        return await self._make_request("GET", path, **kwargs)
