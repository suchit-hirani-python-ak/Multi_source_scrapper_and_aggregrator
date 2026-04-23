import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.scrapers.bookscrape import book_scrape_logic

@pytest.mark.asyncio
async def test_book_scrape_logic_no_html():
    job_id = "test_123"
    mock_redis = AsyncMock()

    mock_categories = {"travel": "https://toscrape.com"}

    mock_book = MagicMock()
    mock_book.h3.a = {"title": "Mock Book Title"}
    mock_book.select_one.side_effect = [
        MagicMock(text="£10.00"),      
        MagicMock(text="In stock"),     
        {"class": ["star-rating", "Five"]} 
    ]


    with patch("app.scrapers.bookscrape.get_all_categories", new_callable=AsyncMock) as mock_get_cats, \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get_http, \
         patch("app.scrapers.bookscrape.BeautifulSoup") as mock_soup, \
         patch("app.scrapers.bookscrape.is_cancelled", return_value=False), \
         patch("app.scrapers.bookscrape.safe_stream", return_value=True), \
         patch("app.scrapers.bookscrape.safe_progress", return_value=True), \
         patch("app.scrapers.bookscrape.safe_complete", return_value=True):


        mock_get_cats.return_value = mock_categories
        mock_get_http.return_value = MagicMock(status_code=200)
        
        instance = mock_soup.return_value
        instance.select.return_value = [mock_book]
        instance.select_one.return_value = None

        results = await book_scrape_logic(job_id, 1, ["travel"], mock_redis, "site")

        assert len(results) == 1
        assert results[0]["title"] == "Mock Book Title"
        assert results[0]["price"] == "£10.00"


@pytest.mark.asyncio
async def test_book_scrape_logic_pagination():
    mock_redis = AsyncMock()
    with patch("app.scrapers.bookscrape.get_all_categories", new_callable=AsyncMock) as m_cats, \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as m_get, \
         patch("app.scrapers.bookscrape.BeautifulSoup") as m_soup:
        
        m_cats.return_value = {"travel": "http://base.com"}
        m_get.return_value = MagicMock(status_code=200)

        mock_next = MagicMock()
        mock_next.__getitem__.return_value = "page-2.html"
        
        soup_inst = m_soup.return_value

        soup_inst.select_one.side_effect = [
            MagicMock(text="£1"), MagicMock(text="In stock"), {"class": ["", "One"]},
            mock_next,
            MagicMock(text="£1"), MagicMock(text="In stock"), {"class": ["", "One"]},
            None       
        ]
        soup_inst.select.return_value = [MagicMock()]

        results = await book_scrape_logic("id", 2, ["travel"], mock_redis, "site")
        assert len(results) == 2

@pytest.mark.asyncio
async def test_book_scrape_logic_cancelled():
    mock_redis = AsyncMock()
    with patch("app.scrapers.bookscrape.get_all_categories", new_callable=AsyncMock) as m_cats:
        m_cats.return_value = {"travel": "url"}

        with patch("app.scrapers.bookscrape.is_cancelled", return_value=True):
            results = await book_scrape_logic("id", 5, ["travel"], mock_redis, "site")
            assert results == []
