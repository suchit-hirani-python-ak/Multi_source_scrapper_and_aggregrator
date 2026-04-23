import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.scrapers.ycombinatorscrape import ycombinator_scrape_logic # Adjust path

@pytest.mark.asyncio
async def test_hn_scrape_success_with_meta_row():
    mock_redis = AsyncMock()
    job_id, limit, site = "hn_123", 1, "hacker-news"

    mock_row = MagicMock()
    mock_row.find.side_effect = [
        MagicMock(), # titleline
        MagicMock(text="Some Title", __getitem__=lambda s, k: "http://link.com"), # title_elem (a tag)
        MagicMock(text="1.")
    ]
    
    mock_meta = MagicMock()
    mock_meta.find.side_effect = [
        MagicMock(text="100 points"), 
        MagicMock(text="pg")
    ]
    mock_row.find_next_sibling.return_value = mock_meta

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("app.scrapers.ycombinatorscrape.BeautifulSoup") as mock_soup, \
         patch("app.scrapers.ycombinatorscrape.is_cancelled", return_value=False), \
         patch("app.scrapers.ycombinatorscrape.safe_stream", return_value=True), \
         patch("app.scrapers.ycombinatorscrape.safe_progress", return_value=True), \
         patch("app.scrapers.ycombinatorscrape.safe_complete", return_value=True):

        mock_get.return_value = MagicMock(status_code=200)
        
        instance = mock_soup.return_value
        instance.find_all.return_value = [mock_row]
        instance.find.return_value = None

        results = await ycombinator_scrape_logic(job_id, limit, ["top"], mock_redis, site)

        assert len(results) == 1
        assert results[0]["author"] == "pg"
        assert results[0]["points"] == "100 points"
        

@pytest.mark.asyncio
async def test_hn_scrape_pagination_and_default_category():
    mock_redis = AsyncMock()
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("app.scrapers.ycombinatorscrape.BeautifulSoup") as mock_soup, \
         patch("app.scrapers.ycombinatorscrape.safe_complete", return_value=True):

        mock_get.return_value = MagicMock(status_code=200)

        mock_more = MagicMock(__getitem__=lambda s, k: "news?p=2")
        
        soup_p1 = MagicMock()
        soup_p1.find_all.return_value = [MagicMock()] 
        soup_p1.find.return_value = mock_more
        
        soup_p2 = MagicMock()
        soup_p2.find_all.return_value = [MagicMock()] 
        soup_p2.find.return_value = None 
        
        mock_soup.side_effect = [soup_p1, soup_p2]
        results = await ycombinator_scrape_logic("id", 2, ["unknown"], mock_redis, "site")
        
        assert len(results) == 2
        assert mock_get.call_count == 2

@pytest.mark.asyncio
async def test_hn_scrape_exception_path():
    mock_redis = AsyncMock()
    with patch("httpx.AsyncClient.get", side_effect=Exception("Timeout")):
        results = await ycombinator_scrape_logic("id", 1, ["top"], mock_redis, "site")
        
        assert results == []
        mock_redis.update_job.assert_called_once() 

@pytest.mark.asyncio
async def test_hn_scrape_cancellation_check():
    mock_redis = AsyncMock()

    with patch("app.scrapers.ycombinatorscrape.is_cancelled", return_value=True):
        results = await ycombinator_scrape_logic("id", 1, ["top"], mock_redis, "site")
        assert results == []
