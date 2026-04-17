"""
API Platform Python SDK - 测试
"""

import pytest
from api_platform import Client
from api_platform.exceptions import APIError, AuthenticationError


class TestClient:
    """客户端测试"""
    
    def test_client_init(self):
        """测试客户端初始化"""
        client = Client(api_key="sk_test_12345678901234567890")
        assert client.api_key == "sk_test_12345678901234567890"
        assert client.base_url == "https://api.platform.com/v1"
        assert client.timeout == 30
        assert client.max_retries == 3
    
    def test_client_custom_config(self):
        """测试自定义配置"""
        client = Client(
            api_key="sk_test_12345678901234567890",
            api_secret="secret",
            base_url="https://custom.api.com/v1",
            timeout=60,
            max_retries=5
        )
        assert client.api_secret == "secret"
        assert client.base_url == "https://custom.api.com/v1"
        assert client.timeout == 60
        assert client.max_retries == 5


class TestExceptions:
    """异常测试"""
    
    def test_api_error(self):
        """测试APIError"""
        error = APIError("测试错误", code=1001, request_id="req_123")
        assert error.message == "测试错误"
        assert error.code == 1001
        assert error.request_id == "req_123"
    
    def test_auth_error(self):
        """测试AuthenticationError"""
        error = AuthenticationError("认证失败", code=401)
        assert error.message == "认证失败"
        assert error.code == 401


class TestUtils:
    """工具函数测试"""
    
    def test_generate_nonce(self):
        """测试生成nonce"""
        from api_platform.utils import generate_nonce
        
        nonce = generate_nonce()
        assert len(nonce) == 32
        
        # 唯一性
        nonce2 = generate_nonce()
        assert nonce != nonce2
    
    def test_validate_api_key(self):
        """测试API Key验证"""
        from api_platform.utils import validate_api_key
        
        assert validate_api_key("sk_test_12345678901234567890") is True
        assert validate_api_key("") is False
        assert validate_api_key("short") is False
    
    def test_mask_api_key(self):
        """测试API Key掩码"""
        from api_platform.utils import mask_api_key
        
        masked = mask_api_key("sk_test_1234567890")
        assert masked == "sk_t...7890"
        
        masked = mask_api_key("")
        assert masked == "***"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
