from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.users import PyObjectId


class SiteName(str, Enum):
    WIKIPEDIA = "wikipedia"
    YCOMBINATOR = "hacker-news"
    YAHOO_FINANCE = "yahoo-finance"
    BOOK_SCRAPE = "book-data"
    QUOTE_SCRAPE = "quote-data"




class JobRequest(BaseModel):
    site: SiteName
    categories: List[str] 
    limit: int = Field(default=50, ge=1, le=100)

    model_config = ConfigDict(use_enum_values=True)


class JobResponse(BaseModel):
    job_id: str
    status: str = "pending"
    message: str = "Scraping job created"


class JobStatusResponse(BaseModel):
    job_id: str
    site: Optional[SiteName] = None
    status: str
    progress: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class JobResultsResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    status: str = "completed"
    results: List[dict] = []

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )