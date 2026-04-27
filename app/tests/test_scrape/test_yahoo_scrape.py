import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.scrapers.yahooscrape import YahooFinanceScraper, yahoo_scrape_logic

@pytest.mark.asyncio
async def test_yahoo_scrape_logic_success():
    mock_redis = AsyncMock()
    job_id = "job123"
    categories = ["apple", "AAPL", "Microsoft"]

    with patch.object(YahooFinanceScraper, "scrape") as mock_scrape, \
         patch("app.scrapers.yahooscrape.is_cancelled", return_value=False), \
         patch("app.scrapers.yahooscrape.safe_stream", return_value=True), \
         patch("app.scrapers.yahooscrape.safe_progress", return_value=True), \
         patch("app.scrapers.yahooscrape.safe_complete", return_value=True):

        mock_scrape.side_effect = [
            {"query": "apple", "ticker": "AAPL"},
            {"query": "AAPL", "ticker": "AAPL"},
            {"query": "Microsoft", "ticker": "MSFT"},
        ]

        results = await yahoo_scrape_logic(job_id, 3, categories, mock_redis, "site")

        assert len(results) == 2

@pytest.mark.asyncio
async def test_resolve_ticker_logic():

    scraper = YahooFinanceScraper()
    
    mock_search_result = MagicMock()
    mock_search_result.quotes = [{"symbol": "AAPL"}]

    with patch("yfinance.Search", return_value=mock_search_result):
        ticker = scraper._resolve_ticker("apple")
        assert ticker == "AAPL"

@pytest.mark.asyncio
async def test_scrape_api_flow():

    scraper = YahooFinanceScraper()
    
    mock_info = {
        "symbol": "AAPL",
        "longName": "Apple Inc.",
        "currentPrice": 180.50,
        "regularMarketChange": 1.25,
        "regularMarketChangePercent": 0.007
    }

    with patch("yfinance.Ticker") as mock_ticker, \
         patch("app.scrapers.yahooscrape.YahooFinanceScraper._resolve_ticker", return_value="AAPL"):
        
        mock_instance = MagicMock()
        mock_instance.info = mock_info
        mock_ticker.return_value = mock_instance

        result = scraper.scrape("apple")

        assert result["ticker"] == "AAPL"
        assert result["company_name"] == "Apple Inc."
        assert result["price"] == 180.50
        assert "yahoo.com" in result["url"]

@pytest.mark.asyncio
async def test_yahoo_exception_and_cancellation():
    mock_redis = AsyncMock()
    
    # Test 1: Exception path
    with patch("app.scrapers.yahooscrape.YahooFinanceScraper.scrape", side_effect=Exception("API Error")):
        results = await yahoo_scrape_logic("id", 1, ["AAPL"], mock_redis, "site")
        assert results == []
        mock_redis.update_job.assert_called_once()

    with patch("app.scrapers.yahooscrape.is_cancelled", return_value=True):
        results = await yahoo_scrape_logic("id", 1, ["AAPL"], mock_redis, "site")
        assert results == []

def test_yahoo_utilities():

    scraper = YahooFinanceScraper()

    assert scraper._normalize_query("  TSLA   ") == "TSLA"
    assert scraper._normalize_query("google inc") == "google inc"
