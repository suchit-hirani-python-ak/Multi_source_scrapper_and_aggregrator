import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.jobscrape_service import ScraperService
from app.schemas.scraper import JobResponse

@pytest.mark.asyncio
async def test_initiate_scrape_cache_hit():

    mock_db = MagicMock()
    mock_redis_client = AsyncMock()
    service = ScraperService(mock_db, mock_redis_client)
    
    service.repo = AsyncMock()
    service.redis = AsyncMock()

    mock_request = MagicMock()
    mock_request.site = "wikipedia"
    mock_request.categories = ["electronics", "books"]
    mock_request.limit = 10
    
    job_id = "660adb23f51bb4362e0020ee"
    service.repo.create_job.return_value = {"_id": job_id}

    cached_data = [{"item": "laptop"}]
    service.redis.get_cache.return_value = cached_data

    result = await service.initiate_scrape(mock_request)

    assert isinstance(result, JobResponse)
    assert result.job_id == job_id

    service.redis.append_to_stream.assert_called_once_with(job_id, cached_data)
    service.repo.save_results.assert_called_once_with(job_id, cached_data)
    service.redis.update_job.assert_any_call(
        job_id=job_id, status="completed", progress=100, site="wikipedia",data=cached_data
    )

@pytest.mark.asyncio
async def test_initiate_scrape_cache_miss_triggers_task():

    mock_db = MagicMock()
    mock_redis_client = AsyncMock()
    service = ScraperService(mock_db, mock_redis_client)
    service.repo = AsyncMock()
    service.redis = AsyncMock()

    mock_request = MagicMock(site="ebay", categories=["toys"], limit=5)
    job_id = "770adb23f51bb4362e0020ff"
    service.repo.create_job.return_value = {"_id": job_id}

    service.redis.get_cache.return_value = None

    with patch("app.services.jobscrape_service.execute_scrape_process.apply_async") as mock_task:
        result = await service.initiate_scrape(mock_request)


        assert result.job_id == job_id

        mock_task.assert_called_once_with(
            args=[job_id, "ebay", ["toys"], 5],
            task_id=job_id
        )

@pytest.mark.asyncio
async def test_get_job_status_success():

    service = ScraperService(MagicMock(), AsyncMock())
    service.redis = AsyncMock()
    
    job_id = "job_123"
    service.redis.get_job.return_value = {
        "status": "processing",
        "progress": "45",
        "site": "amazon"
    }


    with patch("app.services.jobscrape_service.AsyncResult") as mock_result:
        mock_result.return_value.state = "STARTED"
        
        result = await service.get_job_status(job_id)

        # 3. Assertions
        assert result["job_id"] == job_id
        assert result["status"] == "processing"
        assert result["progress"] == 45
        assert result["celery_state"] == "STARTED"

@pytest.mark.asyncio
async def test_get_job_results_not_found():
    service = ScraperService(MagicMock(), AsyncMock())
    service.redis = AsyncMock()
    

    service.redis.get_job.return_value = None

    result = await service.get_job_results("missing_id", 10)

    assert result == {"message": "Job not found"}

@pytest.mark.asyncio
async def test_list_jobs_with_filters():
    service = ScraperService(MagicMock(), AsyncMock())
    service.repo = AsyncMock()
    

    service.repo.get_jobs.return_value = [
        {"_id": "1", "site": "wikipedia", "status": "completed", "created_at": "now"},
        {"_id": "2", "site": "wikipedia", "status": "pending", "created_at": "later"}
    ]

    result = await service.list_jobs(status="completed", site="wikipedia")


    assert len(result) == 2
    assert result[0]["job_id"] == "1"

    service.repo.get_jobs.assert_called_once_with({"status": "completed", "site": "wikipedia"})

@pytest.mark.asyncio
async def test_cancel_job_invalid_state():
    service = ScraperService(MagicMock(), AsyncMock())
    service.redis = AsyncMock()
    

    service.redis.get_job.return_value = {"status": "completed"}

    result = await service.cancel_job("6968578900758")

    assert "Cannot cancel a completed job" in result["message"]
