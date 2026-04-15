from datetime import datetime, timedelta
import json
from typing import Any
from redis.asyncio import Redis

class RedisHelper:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
    
    async def get_cache(self, cache_key: str):
        cached = await self.redis.get(cache_key)
        return json.loads(cached) if cached else None
    
    async def set_cache(self, cache_key: str, data: list):
        # Await the setex call
        await self.redis.setex(cache_key, timedelta(hours=1), json.dumps(data))
        
    async def update_job(self, job_id: str, status: str, progress: int, site: str , data: Any = None):
        payload = {
            "status": status,
            "progress": str(progress),
            "updated_at": datetime.now().isoformat()
        }
        
        if site:
            payload["site"] = site
            # Only set created_at if it's a new job (status pending/starting)
            if status in ["pending", "starting"]:
                payload["created_at"] = datetime.now().isoformat()
        
        if data:
            payload["results"] = json.dumps(data)
        
        await self.redis.hset(job_id, mapping=payload) # type: ignore
        await self.redis.expire(job_id, 7200)

    
    async def append_to_stream(self, job_id: str, chunk_data: list):
        """Append a batch of results as they are fetched."""
        key = f"job:{job_id}:results"
        serialized = [json.dumps(item) for item in chunk_data]
        
        # FIX: Added await to rpush
        await self.redis.rpush(key, *serialized) # type: ignore
        # FIX: Added await to expire
        await self.redis.expire(key, 3600) 

    async def get_paginated_results(self, job_id: str, limit: int) -> list:
        key = f"job:{job_id}:results"
        
        raw_data = await self.redis.lrange(key, 0, limit - 1) # type: ignore
        
        if not raw_data:
            return []
            
        return [json.loads(d) for d in raw_data]
    
    async def get_job(self, job_id: str) -> dict:
        return await self.redis.hgetall(job_id)# type: ignore