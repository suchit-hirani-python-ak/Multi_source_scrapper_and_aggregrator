import pytest
from unittest.mock import AsyncMock, patch
from app.utils.job_control import is_cancelled, safe_stream, safe_progress, safe_complete

@pytest.mark.asyncio
async def test_is_cancelled_true():
    mock_redis = AsyncMock()
    mock_redis.get_job.return_value = {"status": "cancelled"}
    
    cancelled = await is_cancelled(mock_redis, "job_123")
    assert cancelled is True

@pytest.mark.asyncio
async def test_is_cancelled_false():
    mock_redis = AsyncMock()
    mock_redis.get_job.return_value = {"status": "running"}
    assert await is_cancelled(mock_redis, "job_123") is False

    mock_redis.get_job.return_value = None
    assert await is_cancelled(mock_redis, "job_456") is None

@pytest.mark.asyncio
async def test_safe_stream_success():
    mock_redis = AsyncMock()
    mock_redis.get_job.return_value = {"status": "running"}
    batch = [{"data": 1}]
    
    result = await safe_stream(mock_redis, "job_123", batch)
    
    assert result is True
    mock_redis.append_to_stream.assert_called_once_with("job_123", batch)

@pytest.mark.asyncio
async def test_safe_stream_cancelled():
    mock_redis = AsyncMock()
    mock_redis.get_job.return_value = {"status": "cancelled"}
    
    result = await safe_stream(mock_redis, "job_123", [{"data": 1}])
    
    assert result is False
    mock_redis.append_to_stream.assert_not_called()

@pytest.mark.asyncio
async def test_safe_progress_updates():

    mock_redis = AsyncMock()
    mock_redis.get_job.return_value = {"status": "running"}
    
    result = await safe_progress(mock_redis, "job_123", 50, "yahoo")
    
    assert result is True
    mock_redis.update_job.assert_called_with("job_123", "running", 50, "yahoo")

@pytest.mark.asyncio
async def test_safe_complete_logic():

    mock_redis = AsyncMock()

    mock_redis.get_job.return_value = {"status": "running"}
    await safe_complete(mock_redis, "job_1", "site_a")
    mock_redis.update_job.assert_called_with("job_1", "completed", 100, "site_a")

    mock_redis.update_job.reset_mock()
    mock_redis.get_job.return_value = {"status": "cancelled"}
    await safe_complete(mock_redis, "job_2", "site_b")
    mock_redis.update_job.assert_not_called()
