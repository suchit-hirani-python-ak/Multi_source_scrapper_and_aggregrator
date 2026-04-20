async def is_cancelled(redis, job_id):
    job = await redis.get_job(job_id)
    return job and job.get("status") == "cancelled"


async def safe_stream(redis, job_id, batch):
    if not batch:
        return True
    if await is_cancelled(redis, job_id):
        return False
    await redis.append_to_stream(job_id, batch)
    return True


async def safe_progress(redis, job_id, progress, site):
    if await is_cancelled(redis, job_id):
        return False
    await redis.update_job(job_id, "running", progress, site)
    return True


async def safe_complete(redis, job_id, site):
    job = await redis.get_job(job_id)
    if job and job.get("status") != "cancelled":
        await redis.update_job(job_id, "completed", 100, site)