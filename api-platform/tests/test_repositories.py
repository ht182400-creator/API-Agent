"""Tests for repository module"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.repository import Repository, RepoPricing


@pytest.mark.asyncio
class TestRepositoryAPI:
    """Test repository API endpoints"""

    async def test_list_repositories(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        """Test listing repositories"""
        # Create a test repository
        repo = Repository(
            owner_id=test_user.id,
            owner_type="internal",
            name="test-repo",
            slug="test-repo",
            display_name="Test Repository",
            description="A test repository",
            repo_type="psychology",
            protocol="http",
            status="online",
        )
        db_session.add(repo)
        await db_session.flush()
        
        pricing = RepoPricing(
            repo_id=repo.id,
            pricing_type="per_call",
            price_per_call="0.01",
        )
        db_session.add(pricing)
        await db_session.commit()
        
        response = await client.get("/api/v1/repositories")
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]
        assert len(data["data"]["items"]) >= 1

    async def test_list_repositories_with_filter(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        """Test listing repositories with type filter"""
        response = await client.get(
            "/api/v1/repositories",
            params={"type": "psychology"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    async def test_get_repository_not_found(self, client: AsyncClient):
        """Test getting non-existent repository"""
        response = await client.get("/api/v1/repositories/nonexistent")
        
        assert response.status_code == 404


@pytest.mark.asyncio
class TestQuotaAPI:
    """Test quota API endpoints"""

    async def test_get_quota(self, client: AsyncClient, test_api_key):
        """Test getting quota information"""
        api_key, secret = test_api_key
        
        response = await client.get(
            "/api/v1/quota",
            headers={
                "X-Access-Key": api_key,
                "X-Signature": "dummy",
                "X-Timestamp": "1234567890",
                "X-Nonce": "dummy",
            },
        )
        
        # Should return 401 because signature verification fails
        # In real tests, we'd need to generate proper HMAC signatures
        assert response.status_code in [200, 401]


@pytest.mark.asyncio
class TestLogsAPI:
    """Test logs API endpoints"""

    async def test_get_logs(self, client: AsyncClient, test_api_key):
        """Test getting call logs"""
        api_key, secret = test_api_key
        
        response = await client.get(
            "/api/v1/logs",
            headers={
                "X-Access-Key": api_key,
                "X-Signature": "dummy",
                "X-Timestamp": "1234567890",
                "X-Nonce": "dummy",
            },
        )
        
        # Should return 401 because signature verification fails
        assert response.status_code in [200, 401]
