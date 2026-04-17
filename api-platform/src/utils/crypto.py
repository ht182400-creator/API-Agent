"""Crypto utilities - 加密工具"""

import hashlib
import secrets
import base64


def generate_random_string(length: int = 32) -> str:
    """
    Generate a random string
    
    Args:
        length: Length of the string
    
    Returns:
        Random string
    """
    return secrets.token_urlsafe(length)[:length]


def generate_random_hex(length: int = 32) -> str:
    """
    Generate a random hex string
    
    Args:
        length: Length of the hex string
    
    Returns:
        Random hex string
    """
    return secrets.token_hex(length)


def md5_hash(data: str) -> str:
    """
    Calculate MD5 hash
    
    Args:
        data: Data to hash
    
    Returns:
        MD5 hash hex string
    """
    return hashlib.md5(data.encode()).hexdigest()


def sha256_hash(data: str) -> str:
    """
    Calculate SHA256 hash
    
    Args:
        data: Data to hash
    
    Returns:
        SHA256 hash hex string
    """
    return hashlib.sha256(data.encode()).hexdigest()


def sha512_hash(data: str) -> str:
    """
    Calculate SHA512 hash
    
    Args:
        data: Data to hash
    
    Returns:
        SHA512 hash hex string
    """
    return hashlib.sha512(data.encode()).hexdigest()


def base64_encode(data: str) -> str:
    """
    Encode string to base64
    
    Args:
        data: Data to encode
    
    Returns:
        Base64 encoded string
    """
    return base64.b64encode(data.encode()).decode()


def base64_decode(data: str) -> str:
    """
    Decode base64 string
    
    Args:
        data: Base64 encoded string
    
    Returns:
        Decoded string
    """
    return base64.b64decode(data.encode()).decode()


def generate_api_key_id(prefix: str = "key") -> str:
    """
    Generate API key ID
    
    Args:
        prefix: Prefix for the key ID
    
    Returns:
        API key ID
    """
    return f"{prefix}_{generate_random_hex(24)}"


def generate_request_id(prefix: str = "req") -> str:
    """
    Generate request ID
    
    Args:
        prefix: Prefix for the request ID
    
    Returns:
        Request ID
    """
    return f"{prefix}_{generate_random_hex(24)}"
