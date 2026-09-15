"""
敏感信息脱敏测试 —— 评审项 P1-9

覆盖：
1. 键名识别（password / token / api_key / private_key / signature ...）
2. 值内联掩码（Bearer Token / sk_ 开头 Key / JWT / PEM 私钥块）
3. 嵌套结构与容器上限、深度上限、字符串截断
4. sanitize_json_text 的解析与回退行为

用例编号：TC-SAN-xxx
"""

import json

import pytest

from src.utils.sanitize import (
    MASK,
    is_sensitive_key,
    mask_inline_secrets,
    sanitize,
    sanitize_json_text,
)


# ==================== 1. 键名识别 ====================

class TestSensitiveKeyDetection:
    """敏感键名识别"""

    @pytest.mark.parametrize(
        "key",
        [
            "password",
            "user_password",
            "passwd",
            "pwd",
            "api_key",
            "apiKey",
            "X-API-Key",
            "access_key",
            "secret",
            "client_secret",
            "token",
            "access_token",
            "Authorization",
            "private_key",
            "credential",
            "cookie",
            "session_id",
            "sign",
            "signature",
            "nonce",
        ],
    )
    def test_sensitive_keys(self, key):
        """TC-SAN-001: 常见敏感键名应被识别"""
        assert is_sensitive_key(key) is True

    @pytest.mark.parametrize("key", ["username", "email", "amount", "repo_id", "description", "status"])
    def test_normal_keys(self, key):
        """TC-SAN-002: 普通键名不应被误判"""
        assert is_sensitive_key(key) is False


# ==================== 2. 值内联掩码 ====================

class TestInlineMasking:
    """字符串内联凭据掩码"""

    def test_bearer_token_masked(self):
        """TC-SAN-003: Bearer Token 被掩码"""
        result = mask_inline_secrets("Authorization: Bearer abcdefghijklmnop123456")
        assert "abcdefghijklmnop123456" not in result
        assert MASK in result

    def test_api_key_masked(self):
        """TC-SAN-004: sk_ 开头的 API Key 被掩码"""
        result = mask_inline_secrets("key=sk_live_abcdef1234567890")
        assert "sk_live_abcdef1234567890" not in result
        assert MASK in result

    def test_jwt_masked(self):
        """TC-SAN-005: JWT 被掩码"""
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijklmnop"
        result = mask_inline_secrets(f"token={jwt}")
        assert jwt not in result

    def test_pem_private_key_masked(self):
        """TC-SAN-006: PEM 私钥块被整体掩码"""
        pem = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEowIBAAKCAQEAxxxx\n"
            "-----END RSA PRIVATE KEY-----"
        )
        result = mask_inline_secrets(f"private: {pem}")
        assert "MIIEowIBAAKCAQEAxxxx" not in result
        assert MASK in result

    def test_plain_text_untouched(self):
        """TC-SAN-007: 普通文本不被修改"""
        text = "用户提交了一条普通的问答请求"
        assert mask_inline_secrets(text) == text


# ==================== 3. 结构化脱敏 ====================

class TestSanitizeStructure:
    """嵌套结构脱敏"""

    def test_masks_sensitive_fields_keeps_others(self):
        """TC-SAN-008: 敏感字段掩码、普通字段保留"""
        payload = {
            "username": "alice",
            "password": "P@ssw0rd!",
            "amount": 100,
            "nested": {"api_key": "sk_live_secret_value", "repo": "weather"},
        }
        result = sanitize(payload)

        assert result["username"] == "alice"
        assert result["password"] == MASK
        assert result["amount"] == 100
        assert result["nested"]["api_key"] == MASK
        assert result["nested"]["repo"] == "weather"

    def test_handles_list_and_scalars(self):
        """TC-SAN-009: 列表与标量处理"""
        result = sanitize([{"token": "abc"}, 1, None, True, "text"])
        assert result[0]["token"] == MASK
        assert result[1] == 1
        assert result[2] is None
        assert result[3] is True
        assert result[4] == "text"

    def test_depth_limit(self):
        """TC-SAN-010: 超出深度上限时截断"""
        deep = current = {}
        for _ in range(12):
            current["child"] = {}
            current = current["child"]

        result = sanitize(deep, max_depth=3)
        # 逐层下钻，最终应出现截断标记
        node = result
        depth = 0
        while isinstance(node, dict) and "child" in node:
            node = node["child"]
            depth += 1
        assert node == "...<truncated>" or depth < 12

    def test_items_limit(self):
        """TC-SAN-011: 超出条目上限时截断"""
        payload = {f"k{i}": i for i in range(200)}
        result = sanitize(payload, max_items=10)
        assert "__truncated__" in result
        assert len(result) == 11   # 10 条 + 截断标记

    def test_long_string_truncated(self):
        """TC-SAN-012: 超长字符串被截断"""
        result = sanitize("x" * 5000, max_str_len=100)
        assert len(result) < 200
        assert "truncated" in result

    def test_bytes_replaced(self):
        """TC-SAN-013: bytes 仅记录长度，不落库原文"""
        result = sanitize(b"sensitive-binary")
        assert result == "<bytes:16>"

    def test_generic_proxy_body_secrets_masked(self):
        """TC-SAN-014: 通用代理请求体中的凭据被掩码（真实场景）"""
        body = {
            "action": "login",
            "credentials": {"password": "secret123", "mch_key": "mch-secret"},
            "headers": {"Authorization": "Bearer tokentokentoken"},
        }
        result = sanitize(body)
        dumped = json.dumps(result, ensure_ascii=False)
        assert "secret123" not in dumped
        assert "tokentokentoken" not in dumped
        assert result["action"] == "login"


# ==================== 4. JSON 文本脱敏 ====================

class TestSanitizeJsonText:
    """JSON 字符串脱敏"""

    def test_parses_and_masks(self):
        """TC-SAN-015: 合法 JSON 解析后脱敏并保持 JSON 格式"""
        raw = json.dumps({"user": "bob", "password": "pwd123"})
        result = sanitize_json_text(raw)

        parsed = json.loads(result)
        assert parsed["user"] == "bob"
        assert parsed["password"] == MASK

    def test_invalid_json_falls_back_to_text_mask(self):
        """TC-SAN-016: 非法 JSON 回退为文本掩码"""
        result = sanitize_json_text("Authorization: Bearer abcdefghijklmnop12345")
        assert "abcdefghijklmnop12345" not in result

    def test_empty_input(self):
        """TC-SAN-017: 空输入原样返回"""
        assert sanitize_json_text(None) is None
        assert sanitize_json_text("") == ""
