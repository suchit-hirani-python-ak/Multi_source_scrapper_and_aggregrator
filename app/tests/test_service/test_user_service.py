import jwt
import pytest
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from app.services.user_service import UserService
from app.exception.error import BadRequest, NotFound, Unauthorized, Forbidden
from app.schemas.users import UserCreate, UserRole

@pytest.mark.asyncio
async def test_register_user_success():

    mock_db = MagicMock()
    service = UserService(mock_db)
    service.repo = AsyncMock()
    
    user_in = UserCreate(email="test@example.com", password="raw_password")
    service.repo.find_by_email.return_value = None
    service.repo.create_user.return_value = {"email": "test@example.com", "role": "user"}

    with patch("app.services.user_service.hash_password", return_value="hashed_val"):
        result = await service.register_user(user_in)

        assert result["email"] == "test@example.com"
        service.repo.create_user.assert_called_once()

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
    

    with patch("app.services.user_service.generate_tokens", return_value=mock_tokens):
        result = await service.login_user(mock_payload, mock_response)

 
        assert result == mock_tokens
        

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
    
    with patch("jwt.decode", side_effect=jwt.exceptions.ExpiredSignatureError):
        with pytest.raises(Unauthorized) as exc:
            await service.refresh_token("expired_token", MagicMock())
        assert "Refresh token expired" in str(exc.value)

@pytest.mark.asyncio
async def test_register_admin_forbidden():
    service = UserService(MagicMock())
    
    user_in = UserCreate(email="admin@test.com", password="password")
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

@pytest.mark.asyncio
async def test_login_user_invalid_email():
    service = UserService(MagicMock())
    service.repo = AsyncMock()

    service.repo.find_by_email.return_value = None
    mock_payload = MagicMock(username="wrong@test.com")

    with pytest.raises(Unauthorized) as exc:
        await service.login_user(mock_payload, MagicMock())
    assert "Invalid email or password" in str(exc.value)

@pytest.mark.asyncio
async def test_refresh_token_invalid_type():
    service = UserService(MagicMock())

    payload = {"sub": "user@test.com", "type": "access"}
    
    with patch("jwt.decode", return_value=payload):
        with pytest.raises(Unauthorized) as exc:
            await service.refresh_token("wrong_type_token", MagicMock())
        assert "not a refresh token" in str(exc.value)

@pytest.mark.asyncio
async def test_refresh_token_already_revoked():
    service = UserService(MagicMock())
    service.token = AsyncMock()
    
    payload = {"sub": "user@test.com", "type": "refresh"}

    service.token.find_and_revoke.return_value = None

    with patch("jwt.decode", return_value=payload):
        with pytest.raises(Unauthorized) as exc:
            await service.refresh_token("already_used_token", MagicMock())
        assert "Token invalid or already used" in str(exc.value)

@pytest.mark.asyncio
async def test_register_admin_success():
    service = UserService(MagicMock())
    service.repo = AsyncMock()
    
    user_in = UserCreate(email="admin@test.com", password="password")
    service.repo.find_by_email.return_value = None
    service.repo.create_user.return_value = {"email": "admin@test.com", "role": "admin"}

    secret_name = MagicMock()
    secret_name.get_secret_value.return_value = "expected_admin_name"
    secret_pass = MagicMock()
    secret_pass.get_secret_value.return_value = "expected_admin_pass"

    with patch("app.services.user_service.settings") as mock_settings, \
         patch("app.services.user_service.hash_password", return_value="hashed"):
        
        mock_settings.admin_name.get_secret_value.return_value = "expected_admin_name"
        mock_settings.admin_pass.get_secret_value.return_value = "expected_admin_pass"

        result = await service.register_admin(user_in, secret_name, secret_pass)
        
        assert result["role"] == "admin"
        called_args = service.repo.create_user.call_args[0][0]
        assert called_args["role"] == UserRole.ADMIN.value

@pytest.mark.asyncio
async def test_delete_user_account_not_found():
    service = UserService(MagicMock())
    service.repo = AsyncMock()
    
    mock_token_resp = MagicMock(id="missing_user")
    service.repo.remove_user.return_value = False

    with pytest.raises(NotFound) as exc:
        await service.delete_user_account(mock_token_resp)
    assert "User not found" in str(exc.value)
