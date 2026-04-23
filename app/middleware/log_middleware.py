import time
import uuid
from datetime import datetime
from fastapi import Request, Response

async def log_requests_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    
    try:
        response = await call_next(request)
    except Exception as e:
        raise e
    
    execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
    
    path_parts = request.url.path.split("/")
    job_id = path_parts[-1] if "jobs" in path_parts else None

    user_id = None
    if hasattr(request.state, "user"):
        user = request.state.user
        user_id = getattr(user, "id", None) or getattr(user, "email", None)

    log_data = {
        "method": request.method,
        "endpoint": request.url.path,
        "job_id": job_id,
        "user_id": user_id,
        "status_code": response.status_code,
        "response_time_ms": execution_time_ms,
        "is_cached": execution_time_ms, 
        "timestamp": datetime.now().isoformat()
    }

    print(f"Log: {log_data}")

    response.headers["X-Request-ID"] = str(uuid.uuid4())
    return response
