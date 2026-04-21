"""
工具函数模块
提供常用的辅助函数
"""
from datetime import datetime
from typing import Optional, Dict, Any
import hashlib
import uuid


def generate_request_id() -> str:
    """
    生成唯一的请求ID
    
    Returns:
        请求ID字符串，格式: req_{时间戳}_{随机字符}
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = uuid.uuid4().hex[:8]
    return f"req_{timestamp}_{random_str}"


def generate_api_key() -> str:
    """
    生成 API Key
    
    Returns:
        API Key 字符串
    """
    return f"wa_{uuid.uuid4().hex}{uuid.uuid4().hex[:16]}"


def md5_hash(text: str) -> str:
    """
    计算 MD5 哈希值
    
    Args:
        text: 需要哈希的文本
    
    Returns:
        MD5 哈希值（32位十六进制字符串）
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def format_timestamp(dt: Optional[datetime] = None) -> int:
    """
    格式化时间戳
    
    Args:
        dt: datetime 对象，默认为当前时间
    
    Returns:
        Unix 时间戳（秒）
    """
    if dt is None:
        dt = datetime.now()
    return int(dt.timestamp())


def celsius_to_fahrenheit(celsius: float) -> float:
    """
    摄氏度转华氏度
    
    Args:
        celsius: 摄氏温度
    
    Returns:
        华氏温度
    """
    return round(celsius * 9 / 5 + 32, 1)


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    """
    华氏度转摄氏度
    
    Args:
        fahrenheit: 华氏温度
    
    Returns:
        摄氏温度
    """
    return round((fahrenheit - 32) * 5 / 9, 1)


def get_aqi_level(aqi: int) -> Dict[str, Any]:
    """
    根据 AQI 值获取等级信息
    
    Args:
        aqi: 空气质量指数
    
    Returns:
        等级信息字典
    """
    levels = [
        {"min": 0, "max": 50, "level": "优", "color": "#00FF00"},
        {"min": 51, "max": 100, "level": "良", "color": "#90EE90"},
        {"min": 101, "max": 150, "level": "轻度污染", "color": "#FFFF00"},
        {"min": 151, "max": 200, "level": "中度污染", "color": "#FFA500"},
        {"min": 201, "max": 300, "level": "重度污染", "color": "#FF4500"},
        {"min": 301, "max": 500, "level": "严重污染", "color": "#990066"},
    ]
    
    for level_info in levels:
        if level_info["min"] <= aqi <= level_info["max"]:
            return level_info
    
    return levels[-1]


def parse_city_name(city: str) -> str:
    """
    解析城市名称
    
    处理各种输入格式，返回标准城市名
    
    Args:
        city: 城市名称（可能包含特殊字符或空格）
    
    Returns:
        清理后的城市名称
    """
    if not city:
        return ""
    
    # 去除首尾空格
    city = city.strip()
    
    # 移除特殊字符，只保留中文、英文、数字
    city = ''.join(c for c in city if c.isalnum() or c in [' ', '-'])
    
    return city.strip()
