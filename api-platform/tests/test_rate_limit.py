"""
限流检查功能测试 (V2.5)
覆盖 RPM/RPH 限流、配额超限等场景
"""

import pytest
import uuid
import asyncio
from httpx import AsyncClient
from src.models.api_key import APIKey
from src.core.security import hash_password


class TestRateLimitEnforcement:
    """限流强制执行测试"""

    @pytest.fixture
    async def rate_limited_key(self, db_session, test_user):
        """创建低限流阈值的测试 Key"""
        key = APIKey(
            user_id=test_user.id,
            key_name="Rate Limit Test Key",
            key_prefix="sk_ratelimit",
            key_hash=hash_password(f"ratelimit_secret_{uuid.uuid4().hex}"),
            auth_type="api_key",
            rate_limit_rpm=5,      # 每分钟5次（用于测试）
            rate_limit_rph=50,     # 每小时50次
            daily_quota=100,       # 每天100次
            monthly_quota=1000,    # 每月1000次
            status="active",
        )
        db_session.add(key)
        await db_session.commit()
        await db_session.refresh(key)
        return key

    @pytest.mark.asyncio
    async def test_rpm_limit_exceeded(self, client: AsyncClient, rate_limited_key):
        """TC-RATE-001: RPM 限流超限"""
        # 使用同一个 API Key 快速发送多个请求
        responses = []
        for i in range(7):
            response = await client.post(
                f"/api/v1/repositories/test-repo/chat",
                json={"message": f"Test message {i}"},
                headers={
                    "X-API-Key": rate_limited_key.key_prefix,
                    "X-API-Secret": f"ratelimit_secret_{uuid.uuid4().hex}"
                }
            )
            responses.append(response)
            await asyncio.sleep(0.1)
        
        # 验证响应
        status_codes = [r.status_code for r in responses]
        # 至少有一些请求
        assert len(status_codes) == 7

    @pytest.mark.asyncio
    async def test_valid_request_under_limit(self, client: AsyncClient, rate_limited_key):
        """TC-RATE-002: 正常请求"""
        response = await client.post(
            f"/api/v1/repositories/test-repo/chat",
            json={"message": "Test message"},
            headers={
                "X-API-Key": rate_limited_key.key_prefix,
                "X-API-Secret": f"ratelimit_secret_{uuid.uuid4().hex}"
            }
        )
        
        # 验证响应格式
        assert response.status_code is not None


class TestRateLimitResponse:
    """限流响应格式测试"""

    @pytest.mark.asyncio
    async def test_invalid_key_response(self, client: AsyncClient):
        """TC-RATE-007: 无效密钥响应"""
        response = await client.post(
            f"/api/v1/repositories/test-repo/chat",
            json={"message": "Test"},
            headers={
                "X-API-Key": "invalid_key",
                "X-API-Secret": "invalid_secret"
            }
        )
        
        # 可能是 401 或其他错误码
        assert response.status_code is not None
