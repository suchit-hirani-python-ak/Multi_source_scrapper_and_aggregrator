from typing import Optional

from celery.result import AsyncResult
from redis.asyncio import Redis
from pymongo.asynchronous.database import AsyncDatabase
from app.repositories.job_repository import JobRepository
from app.utils.celery import execute_scrape_process
from app.schemas.scraper import JobResponse
from app.utils.redishelper import RedisHelper


class ScraperService:
    def __init__(self, db: AsyncDatabase, redis: Redis):
        self.repo = JobRepository(db)
        self.redis = RedisHelper(redis)

    async def initiate_scrape(self, request) -> JobResponse:
        site_value = request.site
        categories_list = sorted(request.categories)
        limit = request.limit

        job_document = await self.repo.create_job(request)
        job_id = str(job_document["_id"])

        await self.redis.update_job(
            job_id=job_id,
            status="completed",
            progress=0,
            site=site_value
        )


        cache_key = f"cache:{site_value}:{categories_list}:{limit}"
        cached_data = await self.redis.get_cache(cache_key)

        if cached_data:
            await self.redis.append_to_stream(job_id, cached_data)

            await self.redis.update_job(
                job_id=job_id,
                status="completed",
                progress=100,
                site=site_value,
                data=cached_data
            )

            await self.repo.save_results(job_id, cached_data)

            return JobResponse(
                job_id=job_id,
                status="completed",
                message="Scraping job started in background"
            )

        execute_scrape_process.apply_async( # type:ignore
            args=[job_id, site_value, categories_list, limit],
            task_id=job_id
        )

        return JobResponse(
            job_id=job_id,
            status="pending",
            message="Scraping job started in background"
        )


    async def get_job_status(self, job_id: str) -> Optional[dict]:

        data = await self.redis.get_job(job_id)
        
        task = AsyncResult(job_id)
        celery_state = task.state

        if not data and celery_state == "pending":
            return None

        status = data.get("status") if data else celery_state

        return {
            "job_id": job_id,
            "site": data.get("site"),

            "status": status,

            "celery_state": celery_state,

            "progress": int(data.get("progress", 0)),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }

    async def get_job_results(self, job_id: str, limit: int):

        job_data = await self.redis.get_job(job_id)

        if not job_data:
            return {"message": "Job not found"}

        results = await self.redis.get_paginated_results(job_id, limit)

        return {
            "_id": job_id,
            "status": job_data.get("status"),   
            "results": results
        }
    async def list_jobs(self, status: str = None, site: str = None):
        query = {}

        if status:
            query["status"] = status

        if site:
            query["site"] = site

        jobs = await self.repo.get_jobs(query)

        return [
            {
                "job_id": str(job["_id"]),
                "site": job.get("site"),
                "status": job.get("status"),
                "created_at": job.get("created_at")
            }
            for job in jobs
        ]

    async def cancel_job(self, job_id: str):

        job_data = await self.redis.get_job(job_id)

        if not job_data:
            return {"message": "Job not found"}

        current_status = job_data.get("status")

        if current_status in ["completed", "failed"]:
            return {
                "message": f"Cannot cancel a {current_status} job",
                "status": current_status
            }

        if current_status == "cancelled":
            return {
                "message": "Job already cancelled",
                "status": "cancelled"
            }

        await self.redis.update_job(
            job_id=job_id,
            status="cancelled",
            progress=job_data.get("progress", 0),
            site=job_data.get("site")
        )

        return {
            "message": "Job cancelled successfully",
            "status": "cancelled"
        }