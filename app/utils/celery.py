import asyncio
from celery import Celery
from redis.asyncio import Redis, ConnectionPool
from asgiref.sync import async_to_sync
from app.core.config import settings
from app.db.session import db_manager, get_db
from app.repositories.job_repository import JobRepository
from app.repositories.log_repository import LogRepository
from app.scrapers.quotescrape import quote_scrape_logic
from app.scrapers.bookscrape import book_scrape_logic
from app.scrapers.ycombinatorscrape import ycombinator_scrape_logic
from app.utils.redishelper import RedisHelper
from app.scrapers.wikipediascrape import wiki_scrape_logic
from app.scrapers.yahooscrape import yahoo_scrape_logic

celery_app = Celery(
    "worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.utils.celery"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
celery_app.conf.worker_pool = "solo"


async def scrape_wrapper(job_id: str, site: str, categories: list, limit: int):
    pool = ConnectionPool.from_url(
        settings.redis_url,
        decode_responses=True,
        max_connections=20
    )
    redis_client = Redis(connection_pool=pool)

    await db_manager.connect_to_mongo()

    try:
        db = await get_db()
        repo = JobRepository(db)
        r_helper = RedisHelper(redis_client)

        cache_key = f"cache:{site}:{sorted(categories)}:{limit}"
        lock_key = f"lock:{cache_key}"

        cached = await r_helper.get_cache(cache_key)
        if cached:
            await repo.save_results(job_id, cached)
            await r_helper.update_job(job_id, "completed", 100, site, cached)
            return cached

        is_locked = await redis_client.set(lock_key, "1", ex=60, nx=True)

        if not is_locked:
            for _ in range(5):
                await asyncio.sleep(2)
                cached = await r_helper.get_cache(cache_key)
                if cached:
                    await repo.save_results(job_id, cached)
                    return cached


        
        await r_helper.clear_job_results(job_id)

        
        if site == "quote-data":
            results = await quote_scrape_logic(job_id, limit, categories, r_helper, site)
        elif site == "book-data":
            results = await book_scrape_logic(job_id, limit, categories, r_helper, site)
        elif site == "hacker-news":
            results = await ycombinator_scrape_logic(job_id, limit, categories, r_helper, site)
        elif site == "wikipedia":
            results = await wiki_scrape_logic(job_id, limit, categories, r_helper, site)
        elif site == "yahoo-finance":
            results = await yahoo_scrape_logic(job_id, limit, categories, r_helper, site)
        else:
            raise ValueError(f"Unsupported site: {site}")

        if results:
            await repo.save_results(job_id, results)
            await r_helper.set_cache(cache_key, results)

        
        await redis_client.delete(lock_key)

        return results

    finally:
        await redis_client.aclose()
        await pool.aclose()                          
        await db_manager.close_mongo_connection()


@celery_app.task(bind=True, name="execute_scrape_process")
def execute_scrape_process(self, job_id: str, site: str, categories: list, limit: int):
    
    self.update_state(state="RUNNING", meta={"progress": 50})

    try:
        result = async_to_sync(scrape_wrapper)(
            job_id, site, categories, limit
        )

        return result   

    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise e
    
@celery_app.task(name="create_log_task")
def create_log_task(log_data: dict):
    return asyncio.run(async_log_wrapper(log_data))


async def async_log_wrapper(log_data: dict):

    db = db_manager.db

    repo = LogRepository(db)

    return await repo.create_log(log_data)