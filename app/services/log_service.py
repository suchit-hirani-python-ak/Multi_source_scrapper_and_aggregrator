from datetime import datetime
from app.repositories.log_repository import LogRepository


class LogService:

    def __init__(self, db):
        self.repo = LogRepository(db)

    async def log_request(
        self,
        path: str,
        method: str,
        job_id: str,
        response_time: float,
        status_code: int,
        is_cached: bool
    ):
        log_data = {
            "path": path,
            "method": method,
            "job_id": job_id,
            "response_time": round(response_time, 4),
            "status_code": status_code,
            "is_cached": is_cached,
            "timestamp": datetime.utcnow()
        }

        await self.repo.create_log(log_data)