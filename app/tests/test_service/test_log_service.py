import pytest
from unittest.mock import AsyncMock, ANY
from datetime import datetime
from app.services.log_service import LogService

@pytest.mark.asyncio
async def test_log_request_success():
    mock_db = AsyncMock()
    service = LogService(mock_db)
    service.repo.create_log = AsyncMock()

    path = "/api/scrape"
    method = "POST"
    job_id = "job_123"
    response_time = 0.1234567
    status_code = 200
    is_cached = False

    await service.log_request(
        path, method, job_id, response_time, status_code, is_cached
    )

    service.repo.create_log.assert_called_once_with({
        "path": path,
        "method": method,
        "job_id": job_id,
        "response_time": 0.1235,
        "status_code": status_code,
        "is_cached": is_cached,
        "timestamp": ANY
    })

@pytest.mark.asyncio
async def test_log_request_with_none_job_id():
    service = LogService(AsyncMock())
    service.repo.create_log = AsyncMock()

    await service.log_request("/test", "GET", None, 0.5, 200, True)

    called_data = service.repo.create_log.call_args[0][0]
    assert called_data["job_id"] is None
    assert called_data["is_cached"] is True
