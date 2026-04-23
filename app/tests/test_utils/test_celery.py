import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.utils.celery import scrape_wrapper

@pytest.mark.asyncio
async def test_scrape_wrapper_yahoo_finance_execution():
    job_id = "job_456"
    site = "yahoo-finance"
    categories = ["MSFT"]
    limit = 5
    live_results = [{"ticker": "MSFT", "price": 400}]

    mock_redis = AsyncMock()
    mock_redis.set.return_value = True 
    
    mock_repo = AsyncMock()

    with patch("app.utils.celery.Redis", return_value=mock_redis), \
         patch("app.utils.celery.JobRepository", return_value=mock_repo), \
         patch("app.utils.celery.get_db", AsyncMock(return_value=MagicMock())), \
         patch("app.utils.celery.RedisHelper") as MockHelper, \
         patch("app.utils.celery.yahoo_scrape_logic", AsyncMock(return_value=live_results)), \
         patch("app.utils.celery.db_manager.connect_to_mongo", AsyncMock()), \
         patch("app.utils.celery.db_manager.close_mongo_connection", AsyncMock()):

        r_helper_instance = MockHelper.return_value
        r_helper_instance.get_cache = AsyncMock(return_value=None)
        r_helper_instance.clear_job_results = AsyncMock()
        r_helper_instance.set_cache = AsyncMock()

        results = await scrape_wrapper(job_id, site, categories, limit)

        assert results == live_results
        mock_repo.save_results.assert_called_once()
