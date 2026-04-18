"""Crypto utilities - 加密工具"""

import hashlib
import secrets
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from src.config.settings import get_settings


def get_encryption_key() -> bytes:
    """
    获取加密密钥，从配置或环境变量获取
    """
    settings = get_settings()
    secret = settings.api_key_encryption_secret
    # 使用 PBKDF2 派生固定长度的密钥
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"api_key_salt_v1",
        iterations=100000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(secret.encode()))


def encrypt_api_key(api_key: str) -> str:
    """
    加密 API key 用于存储
    
    Args:
        api_key: 原始 API key
        
    Returns:
        Base64 编码的加密字符串
    """
    fernet = Fernet(get_encryption_key())
    encrypted = fernet.encrypt(api_key.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """
    解密 API key
    
    Args:
        encrypted_key: Base64 编码的加密字符串
        
    Returns:
        原始 API key
    """
    fernet = Fernet(get_encryption_key())
    encrypted = base64.urlsafe_b64decode(encrypted_key.encode())
    return fernet.decrypt(encrypted).decode()


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


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage
    
    Args:
        api_key: The API key to hash
    
    Returns:
        SHA256 hash hex string
    """
    return sha256_hash(api_key)


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
