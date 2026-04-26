import pytest
from unittest.mock import patch
from app.services.log_service import LogService


@pytest.mark.asyncio
async def test_log_request_success():
    service = LogService()

    with patch("app.services.log_service.log_task.delay") as mock_task:
        await service.log_request(
            path="/api",
            method="POST",
            status_code=200,
            response_time=0.1234,
            is_cached=False,
            job_id="job1",
            user_id=None
        )

        mock_task.assert_called_once()


@pytest.mark.asyncio
async def test_log_request_with_none_job_id():
    service = LogService()

    with patch("app.services.log_service.log_task.delay") as mock_task:
        await service.log_request(
            path="/api",
            method="GET",
            status_code=200,
            response_time=0.5,
            is_cached=True,
            job_id=None,
            user_id=None
        )

        log_data = mock_task.call_args[0][0]
        assert log_data["job_id"] is None
        assert log_data["is_cached"] is True