from datetime import datetime
from typing import Optional
from pydantic import BaseModel,ConfigDict

from app.schemas.users import UserRole

class TokenResponse(BaseModel):
    id: str
    sub: str       # This contains the email
    role: str      # This contains "admin" or "user"
    exp: int   
    
    model_config = ConfigDict(from_attributes=True)
    @property
    def email(self):
        """Helper to allow calling user.email instead of user.sub"""
        return self.sub

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"