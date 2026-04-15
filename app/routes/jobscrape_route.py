from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException
from pymongo.asynchronous.database import AsyncDatabase
from redis.asyncio import Redis

from app.db.session import get_db
from app.dependencies.dependency import get_redis, get_current_user
from app.schemas.scraper import JobRequest, JobResponse, JobStatusResponse
from app.services.quotescrape_service import ScraperService
from app.schemas.token import TokenResponse # Using your reference

router = APIRouter()

@router.post("/", response_model=JobResponse)
async def create_scrape_job(
    request: JobRequest,
    db: Annotated[AsyncDatabase, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    user: Annotated[TokenResponse, Depends(get_current_user)]
):
    """Initiates a background scraping task via ScraperService"""
    return await ScraperService(db, redis).initiate_scrape(request)

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    db: Annotated[AsyncDatabase, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    user: Annotated[TokenResponse, Depends(get_current_user)]
):
    """Checks the live progress of a job from Redis"""
    # Directly uses the redis helper through the service
    status = await ScraperService(db, redis).get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status

@router.get("/jobs/{job_id}/results")
async def get_job_results(
    job_id: str,
    db: Annotated[AsyncDatabase, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    user: Annotated[TokenResponse, Depends(get_current_user)],
    limit: int = 50,
):
    """Retrieves current results from the Redis stream"""
    return await ScraperService(db, redis).get_job_results(job_id, limit)
