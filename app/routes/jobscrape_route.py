from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pymongo.asynchronous.database import AsyncDatabase
from redis.asyncio import Redis
from app.db.session import get_db
from app.dependencies.dependency import get_redis, get_current_user, allow_admin
from app.schemas.scraper import JobRequest, JobResponse, JobStatusResponse
from app.services.jobscrape_service import ScraperService
from app.schemas.token import TokenResponse

router = APIRouter()


@router.post("/", response_model=JobResponse)
async def create_scrape_job(
    request: Annotated[JobRequest, ...],
    db:    Annotated[AsyncDatabase, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    user:  Annotated[TokenResponse, Depends(get_current_user)]
):
    """Initiates a background scraping task. Request body auto-validated by site type."""
    return await ScraperService(db, redis).initiate_scrape(request)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    db:    Annotated[AsyncDatabase, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    user:  Annotated[TokenResponse, Depends(get_current_user)]
):
    status = await ScraperService(db, redis).get_job_status(job_id)
    return status

@router.get("/jobs/{job_id}/results")
async def get_job_results(
    job_id: str,
    db:    Annotated[AsyncDatabase, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    user:  Annotated[TokenResponse, Depends(get_current_user)],
    limit: int = 50,
):
    return await ScraperService(db, redis).get_job_results(job_id, limit)

@router.get("/jobs")
async def list_jobs(
    db: Annotated[AsyncDatabase, Depends(get_db)],
    user: Annotated[TokenResponse, Depends(allow_admin)],
    status: str = None,
    site: str = None,
):
    service = ScraperService(db, None)
    return await service.list_jobs(status, site)

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    db: Annotated[AsyncDatabase, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    user: Annotated[TokenResponse, Depends(get_current_user)]
):
    service = ScraperService(db, redis)
    return await service.cancel_job(job_id)