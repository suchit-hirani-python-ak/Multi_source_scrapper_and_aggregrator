from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime
from typing import Annotated
from enum import Enum
from pydantic import BeforeValidator

# Helper to handle MongoDB ObjectId as a string in Pydantic
PyObjectId = Annotated[str, BeforeValidator(str)]

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    email: EmailStr
    role: UserRole=UserRole.USER 
    created_at: datetime

    model_config = ConfigDict(from_attributes=True,populate_by_name=True)