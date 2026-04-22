import pytest
from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel
from app.repositories.job_repository import JobRepository # Adjust path

# Mock JobRequest for testing purposes if not imported
class JobRequest(BaseModel):
    name: str
    target_url: str

@pytest.mark.asyncio
async def test_create_job_success(db):
    repo = JobRepository(db)
    request_data = JobRequest(name="Test Scraper", target_url="https://example.com")

    # Execute
    result = await repo.create_job(request_data)

    # Assert persistence and defaults
    assert "_id" in result
    assert result["status"] == "pending"
    assert result["progress"] == 0
    assert isinstance(result["created_at"], datetime)
    
    # Verify in DB
    in_db = await db["ScraperData"].find_one({"_id": result["_id"]})
    assert in_db["name"] == "Test Scraper"

@pytest.mark.asyncio
async def test_update_job_status(db):
    repo = JobRepository(db)
    # Seed a job
    initial = await db["ScraperData"].insert_one({"status": "pending"})
    job_id = str(initial.inserted_id)

    # Execute update
    updated = await repo.update(job_id, {"status": "processing", "progress": 50})

    # Assert
    assert updated is True
    in_db = await db["ScraperData"].find_one({"_id": ObjectId(job_id)})
    assert in_db["status"] == "processing"
    assert in_db["progress"] == 50
    assert "updated_at" in in_db

@pytest.mark.asyncio
async def test_get_by_id_exists(db):
    repo = JobRepository(db)
    job_id = "660adb23f51bb4362e0020ee"
    await db["ScraperData"].insert_one({"_id": ObjectId(job_id), "status": "pending"})

    result = await repo.get_by_id(job_id)

    assert result is not None
    assert str(result["_id"]) == job_id

@pytest.mark.asyncio
async def test_save_results_completes_job(db):
    repo = JobRepository(db)
    initial = await db["ScraperData"].insert_one({"status": "processing"})
    job_id = str(initial.inserted_id)
    results = [{"item": "product1", "price": 10.0}]

    # Execute
    success = await repo.save_results(job_id, results)

    # Assert
    assert success is True
    updated = await db["ScraperData"].find_one({"_id": ObjectId(job_id)})
    assert updated["status"] == "completed"
    assert updated["progress"] == 100
    assert updated["results"] == results

@pytest.mark.asyncio
async def test_get_jobs_with_query(db):
    repo = JobRepository(db)
    # Seed multiple jobs
    await db["ScraperData"].insert_many([
        {"status": "completed", "type": "web"},
        {"status": "pending", "type": "api"},
        {"status": "completed", "type": "api"},
    ])

    # Query for completed jobs
    completed_jobs = await repo.get_jobs({"status": "completed"})

    assert len(completed_jobs) == 2
    assert all(j["status"] == "completed" for j in completed_jobs)
