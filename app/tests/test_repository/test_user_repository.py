import pytest
from bson import ObjectId
from app.repositories.user_repository import UserRepository # Adjust path as needed

@pytest.mark.asyncio
async def test_create_user_success(db):
    repo = UserRepository(db)
    user_data = {
        "email": "test@example.com",
        "password": "hashed_password",
        "role": "user"
    }

    # Execute
    result = await repo.create_user(user_data)

    # Assert
    assert "_id" in result
    assert result["email"] == "test@example.com"
    
    # Verify in DB
    user_in_db = await db["users"].find_one({"email": "test@example.com"})
    assert user_in_db is not None
    assert str(user_in_db["_id"]) == result["_id"]

@pytest.mark.asyncio
async def test_find_by_email_exists(db):
    repo = UserRepository(db)
    email = "find@example.com"
    
    # Seed
    await db["users"].insert_one({"email": email, "role": "user"})

    # Execute
    user = await repo.find_by_email(email)

    # Assert
    assert user is not None
    assert user["email"] == email

@pytest.mark.asyncio
async def test_find_by_id_success(db):
    repo = UserRepository(db)
    user_id = "660adb23f51bb4362e0020ee"
    
    # Seed
    await db["users"].insert_one({"_id": ObjectId(user_id), "email": "id@example.com"})

    # Execute
    user = await repo.find_by_id(user_id)

    # Assert
    assert user is not None
    assert str(user["_id"]) == user_id

@pytest.mark.asyncio
async def test_remove_user_success(db):
    repo = UserRepository(db)
    user_id = "660adb23f51bb4362e0020ff"
    
    # Seed
    await db["users"].insert_one({"_id": ObjectId(user_id)})

    # Execute
    deleted = await repo.remove_user(user_id)

    # Assert
    assert deleted is True
    # Verify gone from DB
    check = await db["users"].find_one({"_id": ObjectId(user_id)})
    assert check is None

@pytest.mark.asyncio
async def test_remove_user_not_found(db):
    repo = UserRepository(db)
    non_existent_id = "660adb23f51bb4362e0020aa"

    # Execute
    deleted = await repo.remove_user(non_existent_id)

    # Assert
    assert deleted is False
