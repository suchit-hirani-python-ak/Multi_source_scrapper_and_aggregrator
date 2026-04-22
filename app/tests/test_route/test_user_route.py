import pytest
from unittest.mock import AsyncMock, patch
from app.schemas.users import UserRole

@pytest.mark.asyncio
async def test_register_endpoint_success(client):
    """Tests POST /register endpoint"""
    # 1. Setup Mock
    with patch("app.services.UserService.register_user", new_callable=AsyncMock) as mock_service:
        mock_service.return_value = {
            "_id": "660adb23f51bb4362e0020ee",
            "email": "test@gmail.com",
            "role": "user",
            "created_at": "2023-01-01T00:00:00"
        }

        # 2. Execute
        response = await client.post(
            "/register", 
            json={"email": "test@gmail.com", "password": "password123"}
        )

        # 3. Assert
        assert response.status_code == 200
        assert response.json()["email"] == "test@gmail.com"
        mock_service.assert_called_once()

@pytest.mark.asyncio
async def test_login_endpoint_success(client):
    """Tests POST /login endpoint"""
    with patch("app.api.v1.auth.UserService.login_user", new_callable=AsyncMock) as mock_service:
        mock_service.return_value = {
            "access_token": "mock_access",
            "refresh_token": "mock_refresh",
            "token_type": "bearer"
        }

        # OAuth2PasswordRequestForm expects data as form-urlencoded, not JSON
        response = await client.post(
            "/login", 
            data={"username": "test@gmail.com", "password": "password123"}
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_setup_admin_endpoint(client):
    """Tests POST /setup-root using Headers"""
    with patch("app.api.v1.auth.UserService.register_admin", new_callable=AsyncMock) as mock_service:
        mock_service.return_value = {
            "_id": "admin_id",
            "email": "admin@test.com",
            "role": "admin",
            "created_at": "2023-01-01T00:00:00"
        }

        response = await client.post(
            "/setup-root",
            json={"email": "admin@test.com", "password": "adminpassword"},
            headers={
                "x-admin-user": "superadmin",
                "x-admin-pass": "supersecret"
            }
        )

        assert response.status_code == 200
        assert response.json()["role"] == "admin"

@pytest.mark.asyncio
async def test_delete_user_endpoint(client):
    """Tests DELETE /delete - uses get_current_user dependency"""
    with patch("app.api.v1.auth.UserService.delete_user_account", new_callable=AsyncMock) as mock_service:
        mock_service.return_value = {"message": "User successfully deleted"}

        # The 'client' fixture already has dependency_overrides for get_current_user
        response = await client.delete("/delete")

        assert response.status_code == 200
        assert response.json()["message"] == "User successfully deleted"
        mock_service.assert_called_once()
