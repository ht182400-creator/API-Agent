"""
API Platform Python SDK - 工具函数
"""

import time
import hashlib
import secrets
from typing import Optional, Dict, Any


def generate_nonce() -> str:
    """
    生成随机nonce
    
    Returns:
        随机字符串
    """
    return secrets.token_hex(16)


def generate_timestamp() -> str:
    """
    生成时间戳（毫秒）
    
    Returns:
        时间戳字符串
    """
    return str(int(time.time() * 1000))


def generate_signature(
    secret: str,
    access_key: str,
    timestamp: str,
    nonce: str,
    body: str = ""
) -> str:
    """
    生成HMAC-SHA256签名
    
    Args:
        secret: 密钥
        access_key: 访问密钥
        timestamp: 时间戳
        nonce: 随机字符串
        body: 请求体
        
    Returns:
        签名
    """
    import hmac
    
    string_to_sign = "\n".join([
        f"AccessKey={access_key}",
        f"Timestamp={timestamp}",
        f"Nonce={nonce}",
        f"BodyHash={hashlib.sha256(body.encode()).hexdigest()}"
    ])
    
    signature = hmac.new(
        secret.encode(),
        string_to_sign.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return signature


def validate_api_key(api_key: str) -> bool:
    """
    验证API Key格式
    
    Args:
        api_key: API Key
        
    Returns:
        是否有效
    """
    if not api_key:
        return False
    
    # 常见格式检查
    if api_key.startswith("sk_"):
        return len(api_key) >= 20
    
    return len(api_key) >= 16


def mask_api_key(api_key: str) -> str:
    """
    掩码API Key
    
    Args:
        api_key: API Key
        
    Returns:
        掩码后的Key
    """
    if not api_key or len(api_key) < 8:
        return "***"
    
    return f"{api_key[:4]}...{api_key[-4:]}"


def format_cost(cost: float) -> str:
    """
    格式化费用显示
    
    Args:
        cost: 费用
        
    Returns:
        格式化后的字符串
    """
    if cost < 0.01:
        return f"{cost * 1000:.2f}厘"
    elif cost < 1:
        return f"{cost * 100:.2f}分"
    else:
        return f"{cost:.2f}元"


def parse_token_count(token_str: str) -> int:
    """
    解析Token数量
    
    Args:
        token_str: Token字符串
        
    Returns:
        Token数量
    """
    if isinstance(token_str, int):
        return token_str
    
    try:
        return int(token_str.replace(",", ""))
    except (ValueError, AttributeError):
        return 0


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并多个字典
    
    Args:
        *dicts: 字典列表
        
    Returns:
        合并后的字典
    """
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result


def filter_none(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    过滤None值
    
    Args:
        d: 字典
        
    Returns:
        过滤后的字典
    """
    return {k: v for k, v in d.items() if v is not None}


class TokenBucket:
    """
    令牌桶限流器
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        初始化令牌桶
        
        Args:
            capacity: 桶容量
            refill_rate: 每秒补充的令牌数
        """
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
    
    def acquire(self, tokens: int = 1) -> bool:
        """
        获取令牌
        
        Args:
            tokens: 需要获取的令牌数
            
        Returns:
            是否获取成功
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False
    
    def _refill(self):
        """补充令牌"""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now
