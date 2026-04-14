from datetime import datetime, timedelta
from app.core.config import settings
import jwt
from fastapi.security import OAuth2PasswordBearer
import redis.asyncio as redis
from passlib.context import CryptContext
redis_client = redis.from_url(settings.redis_url,decode_responses= True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

password_hash = CryptContext(schemes=[settings.encription], deprecated="auto", bcrypt__truncate_error=False)

def hash_password(password: str):
    return password_hash.hash(password)
    
def verify_password(plain: str, hash_pass: str):
    return password_hash.verify(plain,hash_pass)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=settings.access_expire_in_minutes)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode,settings.access_token.get_secret_value(),algorithm=settings.algorithm)

def refresh_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now() + timedelta(days=settings.refresh_expire_in_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode,settings.refresh_token.get_secret_value(),algorithm=settings.algorithm)

def generate_tokens(user:dict):
    access_token = create_access_token(
        data={"sub": user.get("email"),   
        "id": str(user.get("_id")),  
        "role": user.get("role"),    
        "type": "access",}
    )
    refresh_token = refresh_access_token(
        data={"sub":user["email"]}
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "type": "bearer"
    }