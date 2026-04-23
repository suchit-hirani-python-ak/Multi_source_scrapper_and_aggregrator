import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.scrapers.quotescrape import quote_scrape_logic

@pytest.mark.asyncio
async def test_quote_scrape_success_with_pagination():
    mock_redis = AsyncMock()
    job_id, limit, site = "job123", 2, "quotes"
    tags = ["life"]

    def create_mock_quote(text, author):
        q = MagicMock()
        q.find.side_effect = [
            MagicMock(get_text=lambda strip: text),
            MagicMock(get_text=lambda strip: author)
        ]
        return q

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("app.scrapers.quotescrape.BeautifulSoup") as mock_soup, \
         patch("app.scrapers.quotescrape.is_cancelled", return_value=False), \
         patch("app.scrapers.quotescrape.safe_stream", return_value=True), \
         patch("app.scrapers.quotescrape.safe_progress", return_value=True), \
         patch("app.scrapers.quotescrape.safe_complete", return_value=True):

        mock_get.return_value = MagicMock(status_code=200)

        soup_p1 = MagicMock()
        soup_p1.find_all.return_value = [create_mock_quote("Quote 1", "Author 1")]
        soup_p1.find.return_value = MagicMock()

        soup_p2 = MagicMock()
        soup_p2.find_all.return_value = [create_mock_quote("Quote 2", "Author 2")]
        soup_p2.find.return_value = None 

        mock_soup.side_effect = [soup_p1, soup_p2]

        results = await quote_scrape_logic(job_id, limit, tags, mock_redis, site)

        assert len(results) == 2
        assert results[0]["author"] == "Author 1"
        assert results[1]["text"] == "Quote 2"
        assert mock_get.call_count == 2 

@pytest.mark.asyncio
async def test_quote_scrape_exception_handling():
    mock_redis = AsyncMock()

    with patch("httpx.AsyncClient.get", side_effect=Exception("Network Error")):
        results = await quote_scrape_logic("id", 5, ["tag"], mock_redis, "site")
        
        assert results == []
        mock_redis.update_job.assert_called_once()

@pytest.mark.asyncio
async def test_quote_scrape_cancelled():
    mock_redis = AsyncMock()

    with patch("app.scrapers.quotescrape.is_cancelled", side_effect=[False, True]), \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        
        mock_get.return_value = MagicMock(status_code=200)
        results = await quote_scrape_logic("id", 5, ["tag"], mock_redis, "site")
        
        assert results == [] 
