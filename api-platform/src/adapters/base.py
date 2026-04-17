"""Base adapter - 适配器基类"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class AdapterRequest:
    """Adapter request data"""

    endpoint: str
    method: str
    headers: Dict[str, str]
    body: Optional[str] = None
    timeout_ms: int = 30000
    retry_count: int = 3


@dataclass
class AdapterResponse:
    """Adapter response data"""

    status_code: int
    headers: Dict[str, str]
    body: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None


class BaseAdapter(ABC):
    """
    Base adapter class for protocol translation.
    
    Adapters are responsible for translating requests from the platform
    to the protocol expected by each repository backend.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adapter with configuration
        
        Args:
            config: Adapter configuration
        """
        self.config = config

    @property
    @abstractmethod
    def adapter_type(self) -> str:
        """Get adapter type (http, grpc, websocket, etc.)"""
        pass

    @abstractmethod
    async def call(
        self,
        request: AdapterRequest,
    ) -> AdapterResponse:
        """
        Make a call through the adapter
        
        Args:
            request: Adapter request data
        
        Returns:
            Adapter response data
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the adapter and backend are healthy
        
        Returns:
            True if healthy, False otherwise
        """
        pass

    def transform_request(
        self,
        path: str,
        method: str,
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]] = None,
    ) -> AdapterRequest:
        """
        Transform platform request to adapter-specific request
        
        Args:
            path: Request path
            method: HTTP method
            headers: Request headers
            body: Request body
        
        Returns:
            Transformed adapter request
        """
        return AdapterRequest(
            endpoint=path,
            method=method,
            headers=headers,
            body=body,
            timeout_ms=self.config.get("timeout_ms", 30000),
            retry_count=self.config.get("retry_count", 3),
        )

    def transform_response(
        self,
        response: AdapterResponse,
    ) -> Dict[str, Any]:
        """
        Transform adapter response to platform response
        
        Args:
            response: Adapter response
        
        Returns:
            Transformed response dict
        """
        return {
            "status_code": response.status_code,
            "headers": response.headers,
            "body": response.body,
            "latency_ms": response.latency_ms,
            "error": response.error,
        }

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate adapter configuration
        
        Args:
            config: Configuration to validate
        
        Returns:
            True if valid, False otherwise
        """
        required_fields = self.get_required_config_fields()
        
        for field in required_fields:
            if field not in config:
                return False
        
        return True

    def get_required_config_fields(self) -> list[str]:
        """
        Get list of required configuration fields
        
        Returns:
            List of required field names
        """
        return []

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get adapter capabilities
        
        Returns:
            Dict describing adapter capabilities
        """
        return {
            "type": self.adapter_type,
            "auth_methods": [],
            "transform": True,
            "websocket": False,
        }
