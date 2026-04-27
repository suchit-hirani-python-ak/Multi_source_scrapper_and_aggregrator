import time
import uuid
import logging
from datetime import datetime
from fastapi import Request

logger = logging.getLogger(__name__)


async def log_requests_middleware(request: Request, call_next):
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Request failed")
        raise

    execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Extract job_id safely
    path_parts = request.url.path.split("/")
    job_id = path_parts[-1] if "jobs" in path_parts else None

    # Extract user
    user_id = None
    if hasattr(request.state, "user"):
        user = request.state.user
        user_id = getattr(user, "id", None) or getattr(user, "email", None)

    cache_header = response.headers.get("X-Cache", "MISS")
    is_cached = True if cache_header == "HIT" else False

    log_data = {
        "path": request.url.path,
        "method": request.method,
        "job_id": job_id,
        "user_id": user_id,
        "status_code": response.status_code,
        "response_time": execution_time_ms,
        "is_cached": is_cached,
        "timestamp": datetime.utcnow()
    }

    log_service = request.app.state.log_service
    await log_service.log_request(**log_data)

    logger.info(f"Request log: {log_data}")

    response.headers["X-Request-ID"] = str(uuid.uuid4())
    return response