"""Helper utilities - 辅助函数"""

import ipaddress
import re
from typing import Optional, Dict
from datetime import datetime, timezone


def is_ip_allowed(client_ip: Optional[str], allowlist: Optional[str]) -> bool:
    """
    判断直连 IP 是否在支付回调白名单内（用于 IP 级访问控制）。

    Args:
        client_ip: 待校验的直连 IP（如 ``request.client.host``）。
                   缺失（None / "unknown"）时按 **fail-closed** 处理（仅当白名单
                   关闭时才可能放行）。
        allowlist: 逗号分隔的 IPv4/IPv6 地址或 CIDR 网段字符串；
                   ``None`` 或空串 = **校验关闭**（一律放行，保持既有部署行为）。

    Returns:
        bool: 是否放行。

    设计说明：
        - 解析失败的 IP / 网段条目按 fail-closed 处理（不因脏数据放行）；
        - **不要**用 ``X-Forwarded-For`` 作为 client_ip 传入安全决策
          （该头可被任意伪造），反代部署请将代理出口 IP 加入名单。
    """
    if not allowlist or not allowlist.strip():
        return True  # 校验关闭

    if not client_ip or client_ip == "unknown":
        return False  # fail-closed：白名单开启但来源未知

    try:
        addr = ipaddress.ip_address(client_ip.strip())
    except ValueError:
        return False  # 非法 IP → fail-closed

    for entry in allowlist.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            if "/" in entry:
                if addr in ipaddress.ip_network(entry, strict=False):
                    return True
            elif addr == ipaddress.ip_address(entry):
                return True
        except ValueError:
            continue  # 非法配置条目 → 跳过（不因此放行）

    return False


def get_client_ip(request) -> str:
    """
    Extract client IP from request
    
    Args:
        request: FastAPI request object
    
    Returns:
        Client IP address
    """
    # Check for forwarded headers (reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client IP
    if request.client:
        return request.client.host
    
    return "unknown"


def parse_user_agent(user_agent: Optional[str]) -> Dict[str, str]:
    """
    Parse user agent string
    
    Args:
        user_agent: User agent string
    
    Returns:
        Parsed user agent info
    """
    if not user_agent:
        return {
            "browser": "unknown",
            "os": "unknown",
            "device": "unknown",
        }
    
    # Simple parsing (in production, use user-agents library)
    info = {
        "raw": user_agent,
        "browser": "unknown",
        "os": "unknown",
        "device": "unknown",
    }
    
    # Detect OS
    if "Windows" in user_agent:
        info["os"] = "Windows"
    elif "Macintosh" in user_agent or "Mac OS" in user_agent:
        info["os"] = "macOS"
    elif "Linux" in user_agent:
        info["os"] = "Linux"
    elif "Android" in user_agent:
        info["os"] = "Android"
    elif "iOS" in user_agent or "iPhone" in user_agent:
        info["os"] = "iOS"
    
    # Detect browser
    if "Chrome" in user_agent and "Edg" not in user_agent:
        info["browser"] = "Chrome"
    elif "Firefox" in user_agent:
        info["browser"] = "Firefox"
    elif "Safari" in user_agent and "Chrome" not in user_agent:
        info["browser"] = "Safari"
    elif "Edg" in user_agent:
        info["browser"] = "Edge"
    
    # Detect device type
    if "Mobile" in user_agent or "Android" in user_agent:
        info["device"] = "mobile"
    else:
        info["device"] = "desktop"
    
    return info


def utc_now() -> datetime:
    """
    获取当前 UTC 时间（aware datetime，带时区信息）
    用于代码中获取当前时间

    Returns:
        datetime: 当前 UTC 时间（带 timezone.utc 时区信息）
    """
    return datetime.now(timezone.utc)


def get_utc_now() -> callable:
    """
    返回一个用于 SQLAlchemy default 参数的可调用对象
    SQLAlchemy 要求 default 必须是可调用对象，不能是具体值

    Usage:
        created_at = Column(DateTime(timezone=True), default=get_utc_now())

    注意:
        时间列必须声明为 ``DateTime(timezone=True)``（TIMESTAMP WITH TIME ZONE）。
        若声明为无时区的 ``DateTime`` 却使用本函数（返回 aware UTC），
        asyncpg 会抛出：
            ``can't subtract offset-naive and offset-aware datetimes``

    Returns:
        callable: 返回当前 UTC 时间的可调用对象
    """
    return lambda: datetime.now(timezone.utc)


def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    """
    Format datetime to ISO string
    
    Args:
        dt: Datetime to format
    
    Returns:
        ISO formatted string or None
    """
    if dt is None:
        return None
    return dt.isoformat()


def parse_bool(value: Optional[str]) -> bool:
    """
    Parse boolean from string
    
    Args:
        value: String value
    
    Returns:
        Boolean value
    """
    if value is None:
        return False
    
    return value.lower() in ("true", "1", "yes", "on")


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to max length
    
    Args:
        s: String to truncate
        max_length: Maximum length
        suffix: Suffix to append if truncated
    
    Returns:
        Truncated string
    """
    if len(s) <= max_length:
        return s
    
    return s[:max_length - len(suffix)] + suffix


def validate_email(email: str) -> bool:
    """
    Validate email address format
    
    Args:
        email: Email to validate
    
    Returns:
        True if valid, False otherwise
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing unsafe characters
    
    Args:
        filename: Filename to sanitize
    
    Returns:
        Sanitized filename
    """
    # Remove unsafe characters
    safe = re.sub(r"[^\w\s.-]", "", filename)
    # Replace spaces with underscores
    safe = safe.replace(" ", "_")
    return safe


def calculate_percentage(part: float, total: float) -> float:
    """
    Calculate percentage
    
    Args:
        part: Part value
        total: Total value
    
    Returns:
        Percentage (0-100)
    """
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)
