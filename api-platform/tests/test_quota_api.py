"""
配额管理 API 测试
覆盖所有正常案例和异常案例
"""

import pytest
import uuid
from httpx import AsyncClient

from src.models.api_key import APIKey
from src.models.billing import Quota
from src.core.security import hash_password


@pytest.fixture
async def test_api_key(db_session, test_user):
    """创建测试 API Key"""
    key = APIKey(
        user_id=test_user.id,
        key_name="Test API Key",
        key_prefix="sk_test",
        key_hash="test_hash",
        secret_hash="secret_hash",
        auth_type="api_key",
        rate_limit_rpm=1000,
        rate_limit_rph=10000,
        status="active",
    )
    db_session.add(key)
    await db_session.flush()
    return key


class TestQuotaAPI:
    """配额管理 API 测试"""

    @pytest.mark.asyncio
    async def test_get_keys_empty(self, client: AsyncClient, test_user):
        """TC-001: 获取 API Keys 列表 - 空列表"""
        response = await client.get(
            "/api/v1/quota/keys",
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]
        assert "pagination" in data["data"]

    @pytest.mark.asyncio
    async def test_get_keys_with_data(self, client: AsyncClient, test_user, test_api_key):
        """TC-002: 获取 API Keys 列表 - 有数据"""
        response = await client.get(
            "/api/v1/quota/keys",
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) >= 1

    @pytest.mark.asyncio
    async def test_get_keys_pagination(self, client: AsyncClient, test_user):
        """TC-003: 分页功能"""
        response = await client.get(
            "/api/v1/quota/keys",
            params={"page": 1, "page_size": 5},
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["pagination"]["page"] == 1
        assert data["data"]["pagination"]["page_size"] == 5

    @pytest.mark.asyncio
    async def test_create_key_success(self, client: AsyncClient, test_user):
        """TC-004: 成功创建 API Key"""
        response = await client.post(
            "/api/v1/quota/keys",
            json={
                "name": "New Test Key",
                "auth_type": "api_key",
                "rate_limit_rpm": 1000,
                "rate_limit_rph": 10000,
            },
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "api_key" in data["data"]
        assert "secret" in data["data"]
        assert data["data"]["key_name"] == "New Test Key"

    @pytest.mark.asyncio
    async def test_create_key_hmac(self, client: AsyncClient, test_user):
        """TC-005: 创建 HMAC 类型 Key"""
        response = await client.post(
            "/api/v1/quota/keys",
            json={
                "name": "HMAC Key",
                "auth_type": "hmac",
                "rate_limit_rpm": 500,
            },
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["auth_type"] == "hmac"

    @pytest.mark.asyncio
    async def test_create_key_with_quota(self, client: AsyncClient, test_user):
        """TC-006: 创建带配额限制的 Key"""
        response = await client.post(
            "/api/v1/quota/keys",
            json={
                "name": "Quota Key",
                "daily_quota": 1000,
                "monthly_quota": 10000,
            },
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["daily_quota"] == 1000
        assert data["data"]["monthly_quota"] == 10000

    @pytest.mark.asyncio
    async def test_get_key_detail(self, client: AsyncClient, test_user, test_api_key):
        """TC-007: 获取 Key 详情"""
        response = await client.get(
            f"/api/v1/quota/keys/{test_api_key.id}",
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["id"] == str(test_api_key.id)

    @pytest.mark.asyncio
    async def test_get_key_not_found(self, client: AsyncClient, test_user):
        """TC-008: 获取不存在的 Key"""
        fake_id = str(uuid.uuid4())
        response = await client.get(
            f"/api/v1/quota/keys/{fake_id}",
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_key(self, client: AsyncClient, test_user, test_api_key):
        """TC-009: 更新 Key"""
        response = await client.put(
            f"/api/v1/quota/keys/{test_api_key.id}",
            json={
                "key_name": "Updated Key Name",
                "rate_limit_rpm": 2000,
            },
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_disable_key(self, client: AsyncClient, test_user, test_api_key):
        """TC-010: 禁用 Key"""
        response = await client.post(
            f"/api/v1/quota/keys/{test_api_key.id}/disable",
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "disabled"

    @pytest.mark.asyncio
    async def test_enable_key(self, client: AsyncClient, test_user, test_api_key):
        """TC-011: 启用 Key"""
        # 先禁用
        await client.post(
            f"/api/v1/quota/keys/{test_api_key.id}/disable",
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        # 再启用
        response = await client.post(
            f"/api/v1/quota/keys/{test_api_key.id}/enable",
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_delete_key(self, client: AsyncClient, test_user, test_api_key):
        """TC-012: 删除 Key"""
        response = await client.delete(
            f"/api/v1/quota/keys/{test_api_key.id}",
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_set_quota(self, client: AsyncClient, test_user, test_api_key):
        """TC-013: 设置配额限制"""
        response = await client.post(
            f"/api/v1/quota/keys/{test_api_key.id}/set-quota",
            params={"daily_quota": 5000, "monthly_quota": 50000},
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["daily_quota"] == 5000
        assert data["data"]["monthly_quota"] == 50000


class TestQuotaAPIException:
    """配额管理 API 异常测试"""

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """TC-014: 未授权访问"""
        response = await client.get("/api/v1/quota/keys")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token(self, client: AsyncClient):
        """TC-015: 无效 Token"""
        response = await client.get(
            "/api/v1/quota/keys",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_key_without_name(self, client: AsyncClient, test_user):
        """TC-016: 创建 Key 不提供名称"""
        response = await client.post(
            "/api/v1/quota/keys",
            json={"auth_type": "api_key"},
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        # 应该返回验证错误或创建成功（取决于业务逻辑）
        assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_delete_other_user_key(self, client: AsyncClient, db_session, test_user):
        """TC-017: 删除其他用户的 Key"""
        # 创建一个属于另一个用户的 Key
        from src.models.user import User
        
        other_user = User(
            email=f"other_{uuid.uuid4().hex[:8]}@test.com",
            password_hash=hash_password("password123"),
            user_type="developer",
            user_status="active",
        )
        db_session.add(other_user)
        await db_session.flush()
        
        other_key = APIKey(
            user_id=other_user.id,
            key_name="Other User Key",
            key_prefix="sk_other",
            key_hash="hash",
            secret_hash="hash",
            auth_type="api_key",
            status="active",
        )
        db_session.add(other_key)
        await db_session.flush()
        
        # 尝试用当前用户删除
        response = await client.delete(
            f"/api/v1/quota/keys/{other_key.id}",
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_pagination(self, client: AsyncClient, test_user):
        """TC-018: 无效的分页参数"""
        response = await client.get(
            "/api/v1/quota/keys",
            params={"page": -1, "page_size": 1000},
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_rate_limit_zero(self, client: AsyncClient, test_user):
        """TC-019: 设置零速率限制"""
        response = await client.post(
            "/api/v1/quota/keys",
            json={
                "name": "Zero Rate Key",
                "rate_limit_rpm": 0,
            },
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        # 应该创建成功或返回警告
        assert response.status_code in [200, 400, 422]


class TestQuotaOverviewAPI:
    """配额概览 API 测试"""

    @pytest.mark.asyncio
    async def test_get_quota_overview(self, client: AsyncClient, test_user, test_api_key):
        """TC-020: 获取配额概览"""
        response = await client.get(
            "/api/v1/quota/overview",
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)

    @pytest.mark.asyncio
    async def test_get_quota_overview_empty(self, client: AsyncClient, test_user):
        """TC-021: 配额概览 - 无 Keys"""
        response = await client.get(
            "/api/v1/quota/overview",
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []


class TestUsageHistoryAPI:
    """使用历史 API 测试"""

    @pytest.mark.asyncio
    async def test_get_usage_history(self, client: AsyncClient, test_user, test_api_key):
        """TC-022: 获取使用历史"""
        response = await client.get(
            f"/api/v1/quota/usage-history/{test_api_key.id}",
            params={"period_type": "daily", "days": 7},
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_get_usage_history_invalid_key(self, client: AsyncClient, test_user):
        """TC-023: 获取不存在 Key 的使用历史"""
        fake_id = str(uuid.uuid4())
        response = await client.get(
            f"/api/v1/quota/usage-history/{fake_id}",
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200  # 可能返回空数据而不是错误


class TestLogsAPI:
    """日志 API 测试"""

    @pytest.mark.asyncio
    async def test_get_logs(self, client: AsyncClient, test_user):
        """TC-024: 获取调用日志"""
        response = await client.get(
            "/api/v1/quota/logs",
            params={"page": 1, "page_size": 20},
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]
        assert "pagination" in data["data"]

    @pytest.mark.asyncio
    async def test_get_logs_with_filters(self, client: AsyncClient, test_user):
        """TC-025: 带过滤条件的日志查询"""
        response = await client.get(
            "/api/v1/quota/logs",
            params={
                "key_id": str(uuid.uuid4()),
                "repo_id": str(uuid.uuid4()),
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_top_repos(self, client: AsyncClient, test_user, test_api_key):
        """TC-026: 获取使用量最高的仓库"""
        response = await client.get(
            f"/api/v1/quota/top-repos/{test_api_key.id}",
            params={"limit": 10, "days": 30},
            headers={"Authorization": f"Bearer {test_user.access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
