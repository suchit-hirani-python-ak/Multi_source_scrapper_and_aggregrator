import pytest
from unittest.mock import AsyncMock, ANY
from datetime import datetime
from app.services.log_service import LogService

@pytest.mark.asyncio
async def test_log_request_success():
    # 1. Setup Mocks
    mock_db = AsyncMock()
    service = LogService(mock_db)
    # Mock the internal repo method
    service.repo.create_log = AsyncMock()

    # 2. Test Data
    path = "/api/scrape"
    method = "POST"
    job_id = "job_123"
    response_time = 0.1234567  # Testing the round() logic
    status_code = 200
    is_cached = False

    # 3. Execute
    await service.log_request(
        path, method, job_id, response_time, status_code, is_cached
    )

    # 4. Assertions
    service.repo.create_log.assert_called_once_with({
        "path": path,
        "method": method,
        "job_id": job_id,
        "response_time": 0.1235,  # Verify it rounded to 4 decimal places
        "status_code": status_code,
        "is_cached": is_cached,
        "timestamp": ANY          # Use ANY because datetime.utcnow() changes
    })

@pytest.mark.asyncio
async def test_log_request_with_none_job_id():
    service = LogService(AsyncMock())
    service.repo.create_log = AsyncMock()

    # Execute with job_id as None
    await service.log_request("/test", "GET", None, 0.5, 200, True)

    # Verify dictionary still contains the key even if value is None
    called_data = service.repo.create_log.call_args[0][0]
    assert called_data["job_id"] is None
    assert called_data["is_cached"] is True
