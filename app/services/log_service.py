from datetime import datetime
from typing import Optional
import logging
from app.utils.celery import log_task

logger = logging.getLogger(__name__)


class LogService:

    async def log_request(
        self,
        path: str,
        method: str,
        status_code: int,
        response_time: float,
        is_cached: bool,
        job_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:

        try:
            log_data = {
                "path": path,
                "method": method,
                "status_code": status_code,
                "response_time": round(response_time, 4),
                "is_cached": is_cached,
                "job_id": job_id,
                "user_id": user_id,
                "timestamp": datetime.utcnow(),
            }

            log_task.delay(log_data)

        except Exception as e:
            logger.error(f"Logging failed: {e}")