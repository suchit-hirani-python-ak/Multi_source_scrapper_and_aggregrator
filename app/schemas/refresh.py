from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.users import PyObjectId


class RefreshResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: str
    expire_at: datetime
    revoked: bool
    created_at: datetime