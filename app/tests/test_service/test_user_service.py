import jwt
import pytest
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from app.services.user_service import UserService
from app.exception.error import BadRequest, NotFound, Unauthorized, Forbidden
from app.schemas.users import UserCreate, UserRole
from app.dependencies.dependency import get_current_user

@pytest.mark.asyncio
async def test_register_user_success():
    service = UserService(MagicMock())
    service.repo = AsyncMock()
    service.token = AsyncMock()

    user = UserCreate(email="test@example.com", password="raw_password")

    service.repo.find_by_email.return_value = None
    service.repo.create_user.return_value = {
        "_id": "123",
        "email": "test@example.com",
        "role": "user"
    }

    mock_response = MagicMock()

    tokens = {
        "access_token": "access",
        "refresh_token": "refresh"
    }

    with patch("app.services.user_service.hash_password", return_value="hashed"), \
         patch("app.services.user_service.generate_tokens", return_value=tokens):

        result = await service.register_user(user, mock_response)
    assert result == tokens

    mock_response.set_cookie.assert_called_once()

    service.token.create_token.assert_called_once()

@pytest.mark.asyncio
async def test_register_user_exists():
    service = UserService(MagicMock())
    service.repo = AsyncMock()

    service.repo.find_by_email.return_value = {"id": "exists"}

    with pytest.raises(BadRequest):
        await service.register_user(
            UserCreate(email="test@example.com", password="x"),
            MagicMock()
        )

@pytest.mark.asyncio
async def test_login_success():
    service = UserService(MagicMock())
    service.repo = AsyncMock()
    service.token = AsyncMock()

    payload = MagicMock()
    payload.username = "test@example.com"
    payload.password = "plain"

    user = {
        "_id": "123",
        "email": "test@example.com",
        "password": "hashed"
    }
    service.repo.find_by_email.return_value = user

    tokens = {"access_token": "a", "refresh_token": "r"}

    with patch("app.services.user_service.verify_password", return_value=True) as verify, \
        patch("app.services.user_service.generate_tokens", return_value=tokens):

        result = await service.login_user(payload, MagicMock())

        assert result == tokens
        verify.assert_called_once_with("plain", "hashed")

@pytest.mark.asyncio
async def test_login_wrong_password():
    service = UserService(MagicMock())
    service.repo = AsyncMock()

    payload = MagicMock()
    payload.username = "test@example.com"
    payload.password = "wrong"

    service.repo.find_by_email.return_value = {
        "_id": "123",
        "email": "test@example.com",
        "password": "hashed"
    }

    with patch("app.services.user_service.verify_password", return_value=False):
        with pytest.raises(Unauthorized):
            await service.login_user(payload, MagicMock())

@pytest.mark.asyncio
async def test_login_invalid_email():
    service = UserService(MagicMock())
    service.repo = AsyncMock()

    service.repo.find_by_email.return_value = None

    payload = MagicMock()
    payload.username = "wrong@test.com"

    with pytest.raises(Unauthorized):
        await service.login_user(payload, MagicMock())

@pytest.mark.asyncio
async def test_refresh_token_expired():
    service = UserService(MagicMock())

    request = MagicMock()
    request.cookies = {"refresh_token": "token"}

    with patch("jwt.decode", side_effect=jwt.exceptions.ExpiredSignatureError):
        with pytest.raises(Unauthorized):
            await service.refresh_token(request, MagicMock())

@pytest.mark.asyncio
async def test_refresh_token_invalid_type():
    service = UserService(MagicMock())

    request = MagicMock()
    request.cookies = {"refresh_token": "token"}

    payload = {"sub": "user@test.com", "type": "access"}

    with patch("jwt.decode", return_value=payload):
        with pytest.raises(Unauthorized):
            await service.refresh_token(request, MagicMock())

@pytest.mark.asyncio
async def test_refresh_token_already_used():
    service = UserService(MagicMock())
    service.token = AsyncMock()

    request = MagicMock()
    request.cookies = {"refresh_token": "token"}

    payload = {"sub": "user@test.com", "type": "refresh"}
    service.token.find_and_revoke.return_value = None

    with patch("jwt.decode", return_value=payload):
        with pytest.raises(Unauthorized):
            await service.refresh_token(request, MagicMock())

def test_access_token_rejects_refresh():
    payload = {"sub": "user@test.com", "type": "refresh"}

    with patch("jwt.decode", return_value=payload):
        with pytest.raises(Unauthorized):
            get_current_user("fake_token")

@pytest.mark.asyncio
async def test_register_admin_forbidden():
    service = UserService(MagicMock())

    with pytest.raises(Forbidden):
        await service.register_admin(
            UserCreate(email="admin@test.com", password="pass"),
            MagicMock(),
            MagicMock()
        )

@pytest.mark.asyncio
async def test_delete_user_success():
    service = UserService(MagicMock())
    service.repo = AsyncMock()

    service.repo.remove_user.return_value = True

    result = await service.delete_user_account(MagicMock(id="1"))

    assert result["message"] == "User successfully deleted"


@pytest.mark.asyncio
async def test_delete_user_not_found():
    service = UserService(MagicMock())
    service.repo = AsyncMock()

    service.repo.remove_user.return_value = False

    with pytest.raises(NotFound):
        await service.delete_user_account(MagicMock(id="x"))