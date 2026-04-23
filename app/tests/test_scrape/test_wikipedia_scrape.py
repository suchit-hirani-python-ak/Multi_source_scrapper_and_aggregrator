import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.scrapers.wikipediascrape import WikipediaScraper, wiki_scrape_logic

@pytest.mark.asyncio
async def test_wiki_scrape_logic_success():
    mock_redis = AsyncMock()
    job_id = "wiki_job_123"
    categories = ["Python Programming", "FastAPI"]
    site = "wikipedia"

    mock_result = {
        "query": "Python Programming",
        "title": "Python (programming language)",
        "description": "A high-level programming language.",
        "link": "https://wikipedia.org"
    }

    with patch("app.scrapers.wikipediascrape.WikipediaScraper.fetch_one", new_callable=AsyncMock) as mock_fetch, \
         patch("app.scrapers.wikipediascrape.is_cancelled", return_value=False), \
         patch("app.scrapers.wikipediascrape.safe_stream", return_value=True), \
         patch("app.scrapers.wikipediascrape.safe_progress", return_value=True), \
         patch("app.scrapers.wikipediascrape.safe_complete", return_value=True):
        
        mock_fetch.return_value = mock_result

        results = await wiki_scrape_logic(job_id, 2, categories, mock_redis, site)

        assert len(results) == 2
        assert results[0]["title"] == "Python (programming language)"
        assert mock_fetch.call_count == 2

@pytest.mark.asyncio
async def test_fetch_one_api_flow():
    """Tests the actual API call logic inside fetch_one"""
    scraper = WikipediaScraper()

    mock_search_resp = {
        "query": {"search": [{"title": "FastAPI"}]}
    }
    mock_extract_resp = {
        "query": {"pages": {"123": {"extract": "Web framework for Python"}}}
    }

    async with httpx.AsyncClient() as client:
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = [
                MagicMock(status_code=200, json=lambda: mock_search_resp, raise_for_status=lambda: None),
                MagicMock(status_code=200, json=lambda: mock_extract_resp, raise_for_status=lambda: None)
            ]

            result = await scraper.fetch_one(client, "fastapi")

            assert result["title"] == "FastAPI"
            assert "Web framework" in result["description"]
            assert "fastapi" in result["link"].lower()

@pytest.mark.asyncio
async def test_wiki_scrape_exception_and_cancellation():
    mock_redis = AsyncMock()

    with patch("app.scrapers.wikipediascrape.WikipediaScraper.fetch_one", side_effect=Exception("API Down")):
        results = await wiki_scrape_logic("id", 1, ["query"], mock_redis, "site")
        assert results == []
        mock_redis.update_job.assert_called_once()

    with patch("app.scrapers.wikipediascrape.is_cancelled", return_value=True):
        results = await wiki_scrape_logic("id", 1, ["query"], mock_redis, "site")
        assert results == []

def test_wiki_utilities():

    scraper = WikipediaScraper()

    assert scraper._clean_snippet("<p>Hello <b>World</b></p>") == "Hello World"

    assert scraper._normalize_query("  PYTHON   ") == "python"

    assert "Artificial_Intelligence" in scraper._wiki_url("Artificial Intelligence")
