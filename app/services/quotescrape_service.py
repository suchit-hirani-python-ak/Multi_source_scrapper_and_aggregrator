from typing import List, Optional
from app.repositories.job_repository import JobRepository
from redis.asyncio import Redis
from app.utils.celery import execute_scrape_process
from pymongo.asynchronous.database import AsyncDatabase
from app.schemas.scraper import SiteName, JobResponse, JobRequest
from app.utils.redishelper import RedisHelper

class ScraperService:
    def __init__(self, db:AsyncDatabase, redis: Redis):
        self.repo = JobRepository(db)
        self.redis = RedisHelper(redis)

    # Inside ScraperService.initiate_scrape
    async def initiate_scrape(self, request: JobRequest) -> JobResponse:
        site_value = request.site
        # Sorting ensures ['love', 'life'] and ['life', 'love'] hit the same cache
        categories_list = sorted(request.categories) 
        limit = request.limit

        # 1. GENERATE THE KEY
        # If the user changes 'love' to 'humor', this key changes entirely!
        cache_key = f"cache:{site_value}:{categories_list}:{limit}"
        
        # 2. CHECK CACHE
        cached_data = await self.redis.get_cache(cache_key)
        if cached_data:
            # If found, return instantly (No Celery task started)
            return JobResponse(job_id="cached", status="completed", message="Retrieved from cache")

    # 3. IF NOT FOUND (Category changed or new request)
    # Start fresh scrape...


        # 3. Create the job record in MongoDB via Repository
        job_document = await self.repo.create_job(request)
        job_id = str(job_document["_id"])

        # 4. Initialize the job status in Redis for live tracking
        await self.redis.update_job(
            job_id=job_id,
            status="pending",
            progress=0,
            site=request.site
        )

        # 5. Hand off to Celery Worker
        # We pass the values directly because Pydantic handles Enum -> String conversion
        execute_scrape_process.delay(
            job_id=job_id,
            site=site_value,
            categories=categories_list,
            limit=limit
        )

        return JobResponse(
            job_id=job_id,
            status="pending",
            message="Scraping job started in background"
        )


    async def get_job_results(self, job_id: str, limit: int):
        results = await self.redis.get_paginated_results(job_id, limit)
        # Ensure this matches your JobResultsResponse schema exactly
        return {"_id": job_id, "status": "completed", "results": results}

    
    # Inside ScraperService.get_job_status
    async def get_job_status(self, job_id: str) -> Optional[dict]:
        data = await self.redis.get_job(job_id)
        if not data: return None
        
        return {
            "job_id": job_id, # Maps to 'job_id' in schema
            "site": data.get("site"),
            "status": data.get("status"),
            "progress": int(data.get("progress", 0)),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at")
        }
