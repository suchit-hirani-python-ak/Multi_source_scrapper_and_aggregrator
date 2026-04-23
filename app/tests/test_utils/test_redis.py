import pytest
import json
from datetime import timedelta
from unittest.mock import AsyncMock
from app.utils.redishelper import RedisHelper

@pytest.mark.asyncio
async def test_get_cache_success():
    mock_redis = AsyncMock()
    helper = RedisHelper(mock_redis)
    
    mock_data = [{"id": 1, "name": "test"}]
    mock_redis.get.return_value = json.dumps(mock_data)

    result = await helper.get_cache("test_key")
    
    assert result == mock_data
    mock_redis.get.assert_called_once_with("test_key")

@pytest.mark.asyncio
async def test_set_cache():
    mock_redis = AsyncMock()
    helper = RedisHelper(mock_redis)
    data = [{"ticker": "AAPL"}]

    await helper.set_cache("cache_key", data)

    # Verify setex was called with 1 hour (3600 seconds)
    mock_redis.setex.assert_called_once_with(
        "cache_key", 
        timedelta(hours=1), 
        json.dumps(data)
    )

@pytest.mark.asyncio
async def test_update_job_status():
    mock_redis = AsyncMock()
    helper = RedisHelper(mock_redis)
    
    job_id = "job_123"
    await helper.update_job(job_id, "completed", 100, "yahoo-finance")

    # Capture the mapping passed to hset
    args, kwargs = mock_redis.hset.call_args
    mapping = kwargs.get('mapping') or args[1]

    assert mapping["status"] == "completed"
    assert mapping["progress"] == "100"
    assert "updated_at" in mapping
    assert mapping["site"] == "yahoo-finance"
    mock_redis.expire.assert_called_with(job_id, 7200)

@pytest.mark.asyncio
async def test_append_to_stream():
    mock_redis = AsyncMock()
    helper = RedisHelper(mock_redis)
    job_id = "job_abc"
    chunk = [{"item": 1}, {"item": 2}]

    await helper.append_to_stream(job_id, chunk)

    expected_key = f"job:{job_id}:results"
    mock_redis.rpush.assert_called_once()
    mock_redis.expire.assert_called_with(expected_key, 3600)

@pytest.mark.asyncio
async def test_get_paginated_results():

    mock_redis = AsyncMock()
    helper = RedisHelper(mock_redis)
    
    job_id = "job_xyz"
    mock_redis.lrange.return_value = [json.dumps({"data": "val"})]

    results = await helper.get_paginated_results(job_id, 10)

    assert len(results) == 1
    assert results[0]["data"] == "val"
    mock_redis.lrange.assert_called_with(f"job:{job_id}:results", 0, 9)

@pytest.mark.asyncio
async def test_clear_job_results():
    mock_redis = AsyncMock()
    helper = RedisHelper(mock_redis)
    
    await helper.clear_job_results("job_id")

    assert mock_redis.delete.call_count == 2
    mock_redis.delete.assert_any_call("job:job_id:results")
    mock_redis.delete.assert_any_call("job_id")
