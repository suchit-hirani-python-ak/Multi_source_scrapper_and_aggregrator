import pytest
from datetime import datetime, timezone, timedelta
from app.repositories.token_repository import TokenRepository # Adjust path

@pytest.mark.asyncio
async def test_create_token_success(db):
    repo = TokenRepository(db)
    user_id = "660adb23f51bb4362e0020ee"
    token_str = "660adb23f51bb4362e0020ee"
    days = 7


    await repo.create_token(user_id, token_str, days)


    token_in_db = await db["refresh_token"].find_one({"refresh_token": token_str})
    
    assert token_in_db is not None
    assert token_in_db["user_id"] == user_id
    assert token_in_db["revoked"] is False
    expected_expiry = datetime.now(timezone.utc) + timedelta(days=days)
    assert abs((token_in_db["expire_at"].replace(tzinfo=timezone.utc) - expected_expiry).total_seconds()) < 60

@pytest.mark.asyncio
async def test_find_and_revoke_success(db):
    repo = TokenRepository(db)
    token_str = "active_token"
    

    await db["refresh_token"].insert_one({
        "refresh_token": token_str,
        "revoked": False,
        "user_id": "user123"
    })


    result = await repo.find_and_revoke(token_str)


    assert result is not None
    assert result["refresh_token"] == token_str
    assert result["revoked"] is True

    updated_in_db = await db["refresh_token"].find_one({"refresh_token": token_str})
    assert updated_in_db["revoked"] is True

@pytest.mark.asyncio
async def test_find_and_revoke_already_revoked(db):
    repo = TokenRepository(db)
    token_str = "already_revoked_token"
    

    await db["refresh_token"].insert_one({
        "refresh_token": token_str,
        "revoked": True
    })


    result = await repo.find_and_revoke(token_str)

    assert result is None

@pytest.mark.asyncio
async def test_find_and_revoke_non_existent(db):
    repo = TokenRepository(db)
    
    result = await repo.find_and_revoke("non_existent_token")

    assert result is None
