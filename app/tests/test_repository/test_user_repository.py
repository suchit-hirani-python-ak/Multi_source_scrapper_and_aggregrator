import pytest
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError
from app.repositories.user_repository import UserRepository

@pytest.mark.asyncio
async def test_create_user_success(db):
    repo = UserRepository(db)
    user_data = {"email": "success@test.com", "password": "hash", "role": "user"}
    
    result = await repo.create_user(user_data)
    assert "_id" in result
    assert result["email"] == "success@test.com"
    
    db_user = await db["users"].find_one({"email": "success@test.com"})
    assert db_user is not None

@pytest.mark.asyncio
async def test_find_by_email_exists(db):
    repo = UserRepository(db)
    email = "exists@test.com"
    await db["users"].insert_one({"email": email, "role": "user"})

    user = await repo.find_by_email(email)
    assert user is not None
    assert user["email"] == email

@pytest.mark.asyncio
async def test_find_by_id_success(db):
    repo = UserRepository(db)
    user_id = str(ObjectId())
    await db["users"].insert_one({"_id": ObjectId(user_id), "email": "id@test.com"})

    user = await repo.find_by_id(user_id)
    assert str(user["_id"]) == user_id

@pytest.mark.asyncio
async def test_remove_user_success(db):
    repo = UserRepository(db)
    user_id = str(ObjectId())
    await db["users"].insert_one({"_id": ObjectId(user_id)})

    deleted = await repo.remove_user(user_id)
    assert deleted is True
    assert await db["users"].find_one({"_id": ObjectId(user_id)}) is None



@pytest.mark.asyncio
async def test_create_user_duplicate_email(db):

    await db["users"].create_index("email", unique=True)
    repo = UserRepository(db)
    user_data = {"email": "dup@test.com", "password": "123"}
    
    await repo.create_user(user_data)
    with pytest.raises(DuplicateKeyError):
        await repo.create_user(user_data)

@pytest.mark.asyncio
async def test_find_by_email_not_found(db):

    repo = UserRepository(db)
    user = await repo.find_by_email("nonexistent@test.com")
    assert user is None

@pytest.mark.asyncio
async def test_find_by_id_invalid_format(db):

    repo = UserRepository(db)
    with pytest.raises(InvalidId):
        await repo.find_by_id("not-a-valid-id")

@pytest.mark.asyncio
async def test_remove_user_not_found(db):

    repo = UserRepository(db)
    deleted = await repo.remove_user(str(ObjectId()))
    assert deleted is False