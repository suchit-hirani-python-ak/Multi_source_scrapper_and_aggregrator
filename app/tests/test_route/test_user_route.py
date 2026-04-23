import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_register_endpoint_success(client):
    payload = {
        "email": "testuser@example.com",
        "password": "securepassword123"
    }
    
    with patch("app.services.user_service.UserService.register_user", new_callable=AsyncMock) as mock_register:
        mock_register.return_value = {
            "id": "user_123",
            "email": "testuser@example.com",
            "role": "user",
            "created_at": "2026-04-23T05:33:02.405780"
        }

        response = await client.post("auth/register", json=payload)

        assert response.status_code == 200
        assert response.json()["email"] == "testuser@example.com"
        mock_register.assert_called_once()

@pytest.mark.asyncio
async def test_login_endpoint_success(client):
    login_data = {
        "username": "testuser@example.com",
        "password": "securepassword123"
    }

    with patch("app.services.user_service.UserService.login_user", new_callable=AsyncMock) as mock_login:
        mock_login.return_value = {
            "access_token": "fake-access-token",
            "refresh_token": "fake-refresh-token",
            "token_type": "bearer"
        }

        response = await client.post("auth/login", data=login_data)

        assert response.status_code == 200
        assert "access_token" in response.json()
        mock_login.assert_called_once()

@pytest.mark.asyncio
async def test_setup_admin_endpoint(client):
    payload = {
        "email": "admin@example.com",
        "password": "adminpassword"
    }
    headers = {
        "x-admin-user": "superadmin@gmail.com",
        "x-admin-pass": "supersecret"
    }

    with patch("app.services.user_service.UserService.register_admin", new_callable=AsyncMock) as mock_admin:
        mock_admin.return_value = {
            "id": "admin_1",
            "email": "admin@example.com",
            "role": "admin",
            "created_at": "2026-04-23T05:33:02.405780"
        }

        response = await client.post("auth/setup-root", json=payload, headers=headers)

        assert response.status_code == 200
        assert response.json()["email"] == "admin@example.com"
        mock_admin.assert_called_once()

@pytest.mark.asyncio
async def test_delete_user_endpoint(client):

    headers = {"Authorization": "Bearer fake-token"}

    with patch("app.services.user_service.UserService.delete_user_account", new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = {"message": "user deleted"}
        
        response = await client.delete("auth/delete", headers=headers)

        assert response.status_code == 200
        assert response.json()["message"] == "user deleted"
        mock_delete.assert_called_once()
