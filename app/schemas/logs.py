from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class LogSchema(BaseModel):
    path: str
    method: str
    job_id: Optional[str] = None
    response_time: float
    status_code: int
    is_cached: bool = False
    timestamp: datetime