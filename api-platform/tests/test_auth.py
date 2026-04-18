"""Tests for authentication module"""

import pytest
from httpx import AsyncClient

from src.core.security import (
    hash_password,
    verify_password,
    hash_api_key,
    generate_api_key,
    create_access_token,
    verify_token,
)


class TestPasswordHashing:
    """Test password hashing functions"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_success(self):
        """Test password verification with correct password"""
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_failure(self):
        """Test password verification with wrong password"""
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert verify_password("wrongpassword", hashed) is False


class TestAPIKeyGeneration:
    """Test API key generation functions"""

    def test_generate_api_key(self):
        """Test API key generation"""
        api_key, key_hash = generate_api_key("sk_test")
        
        assert api_key.startswith("sk_test_")
        assert len(key_hash) == 64  # SHA256 hash

    def test_hash_api_key(self):
        """Test API key hashing"""
        api_key = "sk_test_abc123"
        hashed = hash_api_key(api_key)
        
        assert len(hashed) == 64
        assert hashed.isalnum()


class TestJWTToken:
    """Test JWT token functions"""

    def test_create_access_token(self):
        """Test access token creation"""
        user_id = "test-user-id"
        token = create_access_token({"sub": user_id})
        
        assert token is not None
        assert len(token) > 0

    def test_verify_token(self):
        """Test token verification"""
        user_id = "test-user-id"
        token = create_access_token({"sub": user_id})
        
        payload = verify_token(token)
        
        assert payload["sub"] == user_id

    def test_verify_invalid_token(self):
        """Test verification of invalid token"""
        from src.core.exceptions import AuthenticationError
        
        with pytest.raises(AuthenticationError):
            verify_token("invalid-token")


@pytest.mark.asyncio
class TestAuthAPI:
    """Test authentication API endpoints"""

    async def test_register(self, client: AsyncClient):
        """Test user registration"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
                "user_type": "developer",
                "role": "user",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["email"] == "newuser@example.com"
        assert data["data"]["username"] == "newuser"
        assert data["data"]["role"] == "user"

    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration with duplicate email"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "password123",
            },
        )
        
        assert response.status_code == 401

    async def test_login_with_email(self, client: AsyncClient, test_user):
        """Test user login with email"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    async def test_login_with_username(self, client: AsyncClient, test_user):
        """Test user login with username"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "testpassword",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "access_token" in data["data"]

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Test login with wrong password"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword",
            },
        )
        
        assert response.status_code == 401
