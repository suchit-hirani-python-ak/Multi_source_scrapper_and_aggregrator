from pymongo import AsyncMongoClient
import pytest
from redis.asyncio import Redis
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from app.core.config import settings
from app.dependencies.dependency import get_current_user
from app.db.session import get_db
from unittest.mock import AsyncMock, MagicMock, patch


TEST_DB = "test_db"
MONGO_URL = settings.mongo_url

@pytest_asyncio.fixture(scope="function")
async def db():
    # Initialize the real async client
    client = AsyncMongoClient(MONGO_URL)
    database = client[TEST_DB]
    
    yield database
    
    # Teardown: Clean up the test database entirely
    try:
        await client.drop_database(TEST_DB)
    finally:
        await client.close()
        
@pytest_asyncio.fixture
async def fake_redis():
    """Provides a fake async Redis client for testing."""
    # Create an instance that mimics redis.asyncio.Redis
    client = Redis(decode_responses=True)
    yield client
    # Cleanup after each test
    await client.flushall()
    await client.close()
    
@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.find_one = AsyncMock()
    db.insert_one = AsyncMock()
    db.update_one = AsyncMock()
    db.delete_one = AsyncMock()
    return db

@pytest_asyncio.fixture
async def client(mock_db):
    with patch("app.dependencies.depandency.redis_client", AsyncMock()):
        mock_user = MagicMock()
        mock_user.id = "660adb23f51bb4362e0020ee"
        mock_user.email = "suchit@gmail.com"
        mock_user.role = "user"

        app.dependency_overrides = {
            get_db: lambda: mock_db,
            get_current_user: lambda: mock_user
        }

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
        app.dependency_overrides.clear()
        
        
@pytest_asyncio.fixture
async def admin_client(client):
    
    mock_admin = MagicMock()
    mock_admin.id = "660adb23f51bb4362e0020ee"
    mock_admin.role = "admin"
    mock_admin.email = "admin@suchit.com"

    
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    
    yield client
    
    app.dependency_overrides.pop(get_current_user, None)