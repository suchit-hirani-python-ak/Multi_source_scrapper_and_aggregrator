import pytest
from datetime import datetime, timezone
from app.repositories.log_repository import LogRepository # Adjust import path

@pytest.mark.asyncio
async def test_create_log_success(db):
    """Verifies that a log entry is successfully saved to the database."""
    repo = LogRepository(db)
    
    log_data = {
        "path": "/api/v1/users",
        "method": "POST",
        "job_id": "job_123",
        "response_time": 0.45,
        "status_code": 201,
        "is_cached": False,
        "timestamp": datetime.now(timezone.utc)
    }

    await repo.create_log(log_data)

    log_in_db = await db["RequestLogs"].find_one({"job_id": "job_123"})
    
    assert log_in_db is not None
    assert log_in_db["path"] == "/api/v1/users"
    assert log_in_db["status_code"] == 201
    assert isinstance(log_in_db["timestamp"], datetime)
