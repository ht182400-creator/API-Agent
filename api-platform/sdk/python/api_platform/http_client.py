"""
API Platform Python SDK - HTTP客户端封装
"""

from typing import Optional, Dict, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import NetworkError, TimeoutError


class HTTPClient:
    """
    HTTP客户端封装
    
    Features:
    - 连接池管理
    - 自动重试
    - 超时控制
    """
    
    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_pool_size: int = 10
    ):
        """
        初始化HTTP客户端
        
        Args:
            base_url: 基础URL
            timeout: 默认超时时间
            max_pool_size: 连接池大小
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        
        # 配置连接池
        adapter = HTTPAdapter(
            pool_connections=max_pool_size,
            pool_maxsize=max_pool_size,
            max_retries=0  # 重试由Client处理
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> requests.Response:
        """
        发起HTTP请求
        
        Args:
            method: HTTP方法
            path: 请求路径
            params: URL参数
            json: JSON请求体
            headers: 请求头
            timeout: 超时时间
            **kwargs: 其他参数
            
        Returns:
            requests.Response对象
            
        Raises:
            NetworkError: 网络错误
            TimeoutError: 超时错误
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        timeout = timeout or self.timeout
        
        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json,
                headers=headers,
                timeout=timeout,
                **kwargs
            )
            return response
            
        except requests.Timeout as e:
            raise TimeoutError(
                message=f"请求超时（{timeout}秒）",
                timeout=timeout
            ) from e
            
        except requests.ConnectionError as e:
            raise NetworkError(
                message=f"网络连接失败：{str(e)}",
                cause=e
            ) from e
            
        except requests.RequestException as e:
            raise NetworkError(
                message=f"请求异常：{str(e)}",
                cause=e
            ) from e
    
    def get(self, path: str, **kwargs) -> requests.Response:
        """GET请求"""
        return self.request("GET", path, **kwargs)
    
    def post(self, path: str, **kwargs) -> requests.Response:
        """POST请求"""
        return self.request("POST", path, **kwargs)
    
    def put(self, path: str, **kwargs) -> requests.Response:
        """PUT请求"""
        return self.request("PUT", path, **kwargs)
    
    def delete(self, path: str, **kwargs) -> requests.Response:
        """DELETE请求"""
        return self.request("DELETE", path, **kwargs)
    
    def close(self):
        """关闭会话"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
