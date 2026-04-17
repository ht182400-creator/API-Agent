"""Helper utilities - 辅助函数"""

import re
from typing import Optional, Dict
from datetime import datetime, timezone


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
    """Get current UTC datetime"""
    return datetime.now(timezone.utc)


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
