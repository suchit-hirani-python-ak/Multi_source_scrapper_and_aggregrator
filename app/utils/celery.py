import asyncio
from celery import Celery
from app.core.config import settings
from app.db.session import db_manager, get_db
from app.repositories.job_repository import JobRepository
from app.scrapers.quotescrape import run_scrape_logic
from app.utils.redishelper import RedisHelper
from app.dependencies.dependency import redis_client

celery_app = Celery(
    "worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.utils.celery"])


celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

async def scrape_wrapper(job_id: str, site: str, categories: list, limit: int):
    await db_manager.connect_to_mongo()
    try:
        db = await get_db()
        repo = JobRepository(db)
        r_helper = RedisHelper(redis_client)
        
        # 1. Run Scraper (updates Redis live via r_helper)
        results = await run_scrape_logic(job_id, limit, categories, r_helper, site)
        
        # 2. SAVE TO MONGO (Crucial for UI persistence)
        if results:
            await repo.save_results(job_id, results)
            
            # 3. Optional: Set long-term cache
            cache_key = f"cache:{site}:{sorted(categories)}:{limit}"
            await r_helper.set_cache(cache_key, results)
            
    finally:
        await db_manager.close_mongo_connection()

        
@celery_app.task(name="execute_scrape_process")
def execute_scrape_process(job_id: str, site: str, categories: list, limit: int):
    return asyncio.run(scrape_wrapper(job_id, site,categories,limit))