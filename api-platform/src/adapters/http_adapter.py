"""HTTP adapter - HTTP适配器"""

import time
import hashlib
from typing import Dict, Any, Optional
from urllib.parse import urljoin

import httpx

from .base import BaseAdapter, AdapterRequest, AdapterResponse


class HTTPAdapter(BaseAdapter):
    """
    HTTP adapter for REST API repositories.
    
    This adapter handles HTTP/HTTPS requests to repository backends.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize HTTP adapter
        
        Args:
            config: Configuration including:
                - base_url: Base URL of the backend API
                - timeout_ms: Request timeout in milliseconds
                - retry_count: Number of retries on failure
                - auth_type: Authentication type (api_key, bearer, hmac, none)
                - headers: Default headers to include
        """
        super().__init__(config)
        self.base_url = config.get("base_url", "")
        self.timeout_ms = config.get("timeout_ms", 30000)
        self.retry_count = config.get("retry_count", 3)
        self.auth_type = config.get("auth_type", "none")
        self.default_headers = config.get("headers", {})
        
        # Create HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout_ms / 1000),
            follow_redirects=True,
        )

    @property
    def adapter_type(self) -> str:
        return "http"

    async def call(
        self,
        request: AdapterRequest,
    ) -> AdapterResponse:
        """
        Make an HTTP request through the adapter
        
        Args:
            request: Adapter request data
        
        Returns:
            Adapter response data
        """
        start_time = time.time()
        
        # Merge headers
        headers = {**self.default_headers, **request.headers}
        
        try:
            # Make HTTP request
            response = await self.client.request(
                method=request.method,
                url=request.endpoint,
                headers=headers,
                content=request.body,
            )
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            return AdapterResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=response.text,
                latency_ms=latency_ms,
            )
            
        except httpx.TimeoutException:
            latency_ms = int((time.time() - start_time) * 1000)
            return AdapterResponse(
                status_code=504,
                headers={},
                body=None,
                latency_ms=latency_ms,
                error="Request timeout",
            )
            
        except httpx.HTTPError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return AdapterResponse(
                status_code=502,
                headers={},
                body=None,
                latency_ms=latency_ms,
                error=f"HTTP error: {str(e)}",
            )

    async def health_check(self) -> bool:
        """
        Check if the backend is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Make a lightweight health check request
            response = await self.client.get("/health", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    def get_required_config_fields(self) -> list[str]:
        """Get required configuration fields"""
        return ["base_url"]

    def get_capabilities(self) -> Dict[str, Any]:
        """Get adapter capabilities"""
        return {
            "type": "http",
            "auth_methods": ["api_key", "bearer", "hmac", "none"],
            "transform": True,
            "websocket": False,
            "streaming": True,
        }

    def add_auth_headers(
        self,
        headers: Dict[str, str],
        api_key: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Add authentication headers based on auth type
        
        Args:
            headers: Existing headers
            api_key: API key
            token: Bearer token
        
        Returns:
            Updated headers
        """
        if self.auth_type == "api_key" and api_key:
            headers["X-API-Key"] = api_key
        elif self.auth_type == "bearer" and token:
            headers["Authorization"] = f"Bearer {token}"
        
        return headers

    def sign_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: Optional[str] = None,
        secret: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Sign request with HMAC
        
        Args:
            method: HTTP method
            path: Request path
            headers: Existing headers
            body: Request body
            secret: HMAC secret
        
        Returns:
            Headers with signature
        """
        if not secret:
            return headers
        
        timestamp = str(int(time.time() * 1000))
        nonce = hashlib.md5(f"{timestamp}{secret}".encode()).hexdigest()
        body_hash = hashlib.sha256(body.encode()).hexdigest() if body else ""
        
        string_to_sign = "\n".join([
            f"Timestamp={timestamp}",
            f"Nonce={nonce}",
            f"Method={method.upper()}",
            f"Path={path}",
            f"BodyHash={body_hash}",
        ])
        
        signature = hashlib.sha256(
            f"{string_to_sign}\n{secret}".encode()
        ).hexdigest()
        
        headers["X-Timestamp"] = timestamp
        headers["X-Nonce"] = nonce
        headers["X-Signature"] = signature
        
        return headers

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
