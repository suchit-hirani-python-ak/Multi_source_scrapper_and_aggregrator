import jwt
import pytest
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from app.services.user_service import UserService
from app.exception.error import BadRequest, Unauthorized, Forbidden
from app.schemas.users import UserCreate, UserRole

@pytest.mark.asyncio
async def test_register_user_success():
    # 1. Setup
    mock_db = MagicMock()
    service = UserService(mock_db)
    service.repo = AsyncMock()
    
    user_in = UserCreate(email="test@example.com", password="raw_password")
    service.repo.find_by_email.return_value = None
    service.repo.create_user.return_value = {"email": "test@example.com", "role": "user"}

    # 2. Patch hash_password to return a fixed string
    with patch("app.services.user_service.hash_password", return_value="hashed_val"):
        result = await service.register_user(user_in)

        # 3. Assertions
        assert result["email"] == "test@example.com"
        service.repo.create_user.assert_called_once()
        # Verify the password was hashed before saving
        called_args = service.repo.create_user.call_args[0][0]
        assert called_args["password"] == "hashed_val"
        assert called_args["role"] == UserRole.USER.value

@pytest.mark.asyncio
async def test_register_user_already_exists():
    service = UserService(MagicMock())
    service.repo = AsyncMock()
    
    service.repo.find_by_email.return_value = {"id": "exists"}
    user_in = UserCreate(email="test@example.com", password="password")

    with pytest.raises(BadRequest) as exc:
        await service.register_user(user_in)
    assert "already exists" in str(exc.value)

@pytest.mark.asyncio
async def test_login_user_success():
    # 1. Setup
    service = UserService(MagicMock())
    service.repo = AsyncMock()
    service.token = AsyncMock()
    
    mock_payload = MagicMock()
    mock_payload.username = "test@example.com"
    mock_response = MagicMock()
    
    user_id = "660adb23f51bb4362e0020ee"
    user_db = {"_id": user_id, "email": "test@example.com"}
    service.repo.find_by_email.return_value = user_db

    mock_tokens = {"access_token": "at", "refresh_token": "rt"}
    
    # 2. Execute
    with patch("app.services.user_service.generate_tokens", return_value=mock_tokens):
        result = await service.login_user(mock_payload, mock_response)

        # 3. Basic Assertions
        assert result == mock_tokens
        
        # Verify Token Repository was called correctly
        service.token.create_token.assert_called_once_with(
            user_id=user_id, 
            token_str="rt", 
            days_valid=ANY  
        )
        
        
        mock_response.set_cookie.assert_called_once_with(
            key="refresh_token",
            value="rt",
            httponly=True,
            secure=False,  
            samesite="lax",
            max_age=ANY    
        )


@pytest.mark.asyncio
async def test_refresh_token_expired():
    service = UserService(MagicMock())
    
    # Mock jwt.decode to raise Expired Error
    with patch("jwt.decode", side_effect=jwt.exceptions.ExpiredSignatureError):
        with pytest.raises(Unauthorized) as exc:
            await service.refresh_token("expired_token", MagicMock())
        assert "Refresh token expired" in str(exc.value)

@pytest.mark.asyncio
async def test_register_admin_forbidden():
    service = UserService(MagicMock())
    
    user_in = UserCreate(email="admin@test.com", password="password")
    # Wrong secrets
    secret_name = MagicMock()
    secret_name.get_secret_value.return_value = "wrong"
    secret_pass = MagicMock()
    secret_pass.get_secret_value.return_value = "wrong"

    with pytest.raises(Forbidden):
        await service.register_admin(user_in, secret_name, secret_pass)

@pytest.mark.asyncio
async def test_delete_user_account_success():
    service = UserService(MagicMock())
    service.repo = AsyncMock()
    
    mock_token_resp = MagicMock(id="user_123")
    service.repo.remove_user.return_value = True

    result = await service.delete_user_account(mock_token_resp)

    assert result["message"] == "User successfully deleted"
    service.repo.remove_user.assert_called_once_with("user_123")
