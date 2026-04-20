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
        await self.redis.setex(cache_key, timedelta(hours=1), json.dumps(data))

    async def clear_job_results(self, job_id: str):
        await self.redis.delete(f"job:{job_id}:results")
        await self.redis.delete(job_id)

    async def update_job(self, job_id: str, status: str, progress: int, site: str, data: Any = None):
        payload = {
            "status": status,
            "progress": str(progress),
            "updated_at": datetime.now().isoformat()
        }

        if site:
            payload["site"] = site
            if status in ["pending", "starting"]:
                payload["created_at"] = datetime.now().isoformat()

        if data:
            payload["results"] = json.dumps(data)

        await self.redis.hset(job_id, mapping=payload)
        await self.redis.expire(job_id, 7200)

    async def append_to_stream(self, job_id: str, chunk_data: list):
        key = f"job:{job_id}:results"
        serialized = [json.dumps(item) for item in chunk_data]

        await self.redis.rpush(key, *serialized)
        await self.redis.expire(key, 3600)

    async def get_paginated_results(self, job_id: str, limit: int) -> list:
        key = f"job:{job_id}:results"
        raw_data = await self.redis.lrange(key, 0, limit - 1)
        return [json.loads(d) for d in raw_data] if raw_data else []

    async def get_job(self, job_id: str) -> dict:
        return await self.redis.hgetall(job_id)