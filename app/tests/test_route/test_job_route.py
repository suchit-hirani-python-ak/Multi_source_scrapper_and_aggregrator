import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_create_scrape_job_success(client):
    payload = {
        "site": "wikipedia",
        "categories": ["Artificial Intelligence"],
        "limit": 50
    }

    with patch("app.services.jobscrape_service.ScraperService.initiate_scrape", new_callable=AsyncMock) as mock_initiate:
        mock_initiate.return_value = {
            "job_id": "job_999",
            "status": "pending",
            "message": "Scraping job started in background"
        }

        response = await client.post("/scrape/", json=payload)

        assert response.status_code == 200
        assert response.json()["job_id"] == "job_999"
        mock_initiate.assert_called_once()

@pytest.mark.asyncio
async def test_get_job_status_success(client):
    job_id = "job_999"
    
    with patch("app.services.jobscrape_service.ScraperService.get_job_status", new_callable=AsyncMock) as mock_status:
        mock_status.return_value = {
            "job_id": job_id,
            "status": "completed",
            "progress": 100
        }

        response = await client.get(f"/scrape/jobs/{job_id}")

        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        mock_status.assert_called_once_with(job_id)

@pytest.mark.asyncio
async def test_get_job_results_success(client):
    job_id = "job_999"
    
    with patch("app.services.jobscrape_service.ScraperService.get_job_results", new_callable=AsyncMock) as mock_results:
        mock_results.return_value = [{"title": "DevOps Engineer", "company": "Tech Corp"}]

        response = await client.get(f"/scrape/jobs/{job_id}/results?limit=10")

        assert response.status_code == 200
        assert len(response.json()) == 1
        mock_results.assert_called_once()

@pytest.mark.asyncio
async def test_list_jobs_admin_only(admin_client):
    
    with patch("app.services.jobscrape_service.ScraperService.list_jobs", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [{"job_id": "job_1"}, {"job_id": "job_2"}]

        response = await admin_client.get("/scrape/jobs")

        assert response.status_code == 200
        assert isinstance(response.json(), list)
        mock_list.assert_called_once()

@pytest.mark.asyncio
async def test_cancel_job_success(client):
    job_id = "job_999"
    
    with patch("app.services.jobscrape_service.ScraperService.cancel_job", new_callable=AsyncMock) as mock_cancel:
        mock_cancel.return_value = {"message": "Job cancelled successfully"}

        response = await client.post(f"/scrape/jobs/{job_id}/cancel")

        assert response.status_code == 200
        assert "successfully" in response.json()["message"]
        mock_cancel.assert_called_once_with(job_id)
