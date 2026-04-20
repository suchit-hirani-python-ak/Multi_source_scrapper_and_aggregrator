import time
import uuid
from datetime import datetime
from fastapi import Request

from app.utils.celery import create_log_task


async def log_requests_middleware(request: Request, call_next):

    start_time = time.perf_counter()

    response = None

    try:
        response = await call_next(request)
    except Exception as e:
        raise e
    finally:
        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 🔹 Extract job_id
        job_id = None
        if request.path_params:
            job_id = request.path_params.get("job_id")

        # 🔹 Extract user_id
        user_id = None
        if hasattr(request.state, "user"):
            user = request.state.user
            user_id = getattr(user, "id", None) or getattr(user, "email", None)

        log_data = {
            "method": request.method,
            "endpoint": request.url.path,
            "job_id": job_id,
            "user_id": user_id,
            "status_code": response.status_code if response else 500,
            "response_time_ms": execution_time_ms,
            "is_cached": execution_time_ms < 200,
            "timestamp": datetime.utcnow().isoformat()
        }

        # 🚀 Async logging
        create_log_task.delay(log_data)

        if response:
            response.headers["X-Request-ID"] = str(uuid.uuid4())

    return response