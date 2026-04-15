from datetime import datetime, timezone
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.users import PyObjectId



class SiteName(str, Enum):
    WIKIPEDIA = "wikipedia"
    YCOMBINATOR = "Hacker news"
    YAHOO_FINANCE = "yahoo finance"
    BOOK_SCRAPE = "book-data"
    QUOTE_SCRAPE = "quote-data"

    
class QuoteScrape(str, Enum):
    LOVE = "love"
    INSPIRATIONAL = "inspirational"
    LIFE = "life"
    HUMOR = "humor"
    BOOKS = "books"
    READING = "reading"
    FRIENDSHIP = "friendship"
    TRUTH = "truth"
    


class QuoteParams(BaseModel):
    site: Literal[SiteName.QUOTE_SCRAPE] = SiteName.QUOTE_SCRAPE
    categories: List[QuoteScrape]
    limit: int = Field(50, ge=1)

class JobRequest(BaseModel):
    # This creates your dropdown select
    site: SiteName
    categories: List[QuoteScrape] = Field(..., description="Multi-select categories")
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
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    
class JobResultsResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    status: str = "completed"
    results: Optional[List[dict]]
    