"""
敏感信息脱敏工具（日志 / 审计 / 操作日志安全）

背景（评审项 P1-9）：
    平台会把请求参数、审计新旧值、操作日志等写入数据库
    （`api_call_logs.request_params`、`audit_logs.old_data/new_data`、
    `user_operation_logs.request_data/old_values/new_values`）。
    若其中包含密码、Token、API Key、私钥等敏感字段，会造成隐私与合规风险。

方案：
    1. 按"键名"识别敏感字段并整体掩码（如 password、token、private_key）；
    2. 按"值内容"对常见凭据模式做内联掩码（如 Bearer Token、sk_ 开头的 Key）；
    3. 对深度、条目数、字符串长度做上限，避免超大 payload 撑爆日志表。

使用方式：
    from src.utils.sanitize import sanitize, sanitize_json_text

    request_params=json.dumps(sanitize(params), ensure_ascii=False)
    old_data=sanitize(old_dict)
"""

import json
import re
from typing import Any, Optional

# 掩码占位符
MASK = "***"

# 键名中包含以下片段（去掉非字母数字后）即视为敏感字段
SENSITIVE_KEY_HINTS = (
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "authorization",
    "apikey",
    "accesskey",
    "privatekey",
    "credential",
    "cookie",
    "session",
    "sign",
    "signature",
    "nonce",
    "mchno",
)

# 值内联掩码规则
_INLINE_PATTERNS = (
    # Authorization: Bearer xxx / Bearer xxx
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]+"), "Bearer " + MASK),
    # API Key：sk_live_xxx / sk_test_xxx / sk_xxx
    (re.compile(r"\bsk_[A-Za-z0-9_\-]{6,}"), MASK),
    # PEM 私钥块
    (
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
        MASK,
    ),
    # JWT（三段式）
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"), MASK),
)

# 默认上限
DEFAULT_MAX_DEPTH = 8
DEFAULT_MAX_ITEMS = 100
DEFAULT_MAX_STR_LEN = 1000
TRUNCATED_FLAG = "...<truncated>"


def _normalize_key(key: Any) -> str:
    """归一化键名：转小写并去掉非字母数字字符（x-api-key -> xapikey）"""
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def is_sensitive_key(key: Any) -> bool:
    """判断键名是否敏感"""
    normalized = _normalize_key(key)
    return any(hint in normalized for hint in SENSITIVE_KEY_HINTS)


def mask_inline_secrets(text: str) -> str:
    """对字符串中的常见凭据模式做内联掩码"""
    result = text
    for pattern, replacement in _INLINE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def sanitize(
    value: Any,
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_items: int = DEFAULT_MAX_ITEMS,
    max_str_len: int = DEFAULT_MAX_STR_LEN,
    _depth: int = 0,
) -> Any:
    """
    递归脱敏任意可序列化对象。

    Args:
        value: 待脱敏对象（dict / list / str / 标量）
        max_depth: 最大递归深度，超出仅保留截断标记
        max_items: 容器（dict/list）最大保留条目数
        max_str_len: 字符串最大长度

    Returns:
        脱敏后的同构对象（可直接用于 JSON 序列化或 JSONB 存储）
    """
    if _depth >= max_depth:
        return TRUNCATED_FLAG

    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, str):
        masked = mask_inline_secrets(value)
        if len(masked) > max_str_len:
            return masked[:max_str_len] + TRUNCATED_FLAG
        return masked

    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"

    if isinstance(value, dict):
        result = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= max_items:
                result["__truncated__"] = f"还有 {len(value) - max_items} 项未记录"
                break
            if is_sensitive_key(key):
                result[str(key)] = MASK
            else:
                result[str(key)] = sanitize(
                    item,
                    max_depth=max_depth,
                    max_items=max_items,
                    max_str_len=max_str_len,
                    _depth=_depth + 1,
                )
        return result

    if isinstance(value, (list, tuple, set)):
        items = list(value)
        result = [
            sanitize(
                item,
                max_depth=max_depth,
                max_items=max_items,
                max_str_len=max_str_len,
                _depth=_depth + 1,
            )
            for item in items[:max_items]
        ]
        if len(items) > max_items:
            result.append(f"...<truncated {len(items) - max_items} items>")
        return result

    # 其他类型统一转为字符串并做内联掩码
    text = mask_inline_secrets(str(value))
    return text if len(text) <= max_str_len else text[:max_str_len] + TRUNCATED_FLAG


def sanitize_json_text(
    text: Optional[str],
    *,
    max_str_len: int = 2000,
) -> Optional[str]:
    """
    对"已经是 JSON 字符串"的内容脱敏。

    解析成功 → 脱敏后重新序列化；
    解析失败 → 按纯文本做内联掩码并截断（避免丢失信息）。

    Args:
        text: JSON 字符串或普通文本
        max_str_len: 回退为纯文本时的最大长度

    Returns:
        脱敏后的字符串；输入为空时返回 None
    """
    if not text:
        return text
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        masked = mask_inline_secrets(str(text))
        return masked if len(masked) <= max_str_len else masked[:max_str_len] + TRUNCATED_FLAG

    return json.dumps(sanitize(parsed), ensure_ascii=False, default=str)
