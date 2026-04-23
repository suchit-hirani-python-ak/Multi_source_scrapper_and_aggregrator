from pydantic import BaseModel,ConfigDict

from app.schemas.users import UserRole

class TokenResponse(BaseModel):
    id: str
    sub: str       
    role: str     
    exp: int   
    
    model_config = ConfigDict(from_attributes=True)
    @property
    def email(self):
        return self.sub

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"