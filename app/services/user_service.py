from datetime import datetime, timedelta
from pydantic import SecretStr
from app.core.config import settings
import jwt
from pymongo.asynchronous.database import AsyncDatabase
from app.core.security import generate_tokens, hash_password, redis_client, verify_password
from fastapi import Response
from fastapi.security import OAuth2PasswordRequestForm
from app.exception.error import BadRequest, Forbidden, NotFound, Unauthorized
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.token import Token, TokenResponse
from app.schemas.users import UserCreate, UserResponse, UserRole

class UserService:
    def __init__(self, db: AsyncDatabase):
        self.repo = UserRepository(db)
        self.token = TokenRepository(db)

    async def register_user(self, user_in: UserCreate):
        if await self.repo.find_by_email(user_in.email):
            raise BadRequest("User already exists")


        user_dict = user_in.model_dump()
        user_dict["role"] = UserRole.USER.value
        user_dict["password"] = hash_password(user_in.password)
        
        user_dict["created_at"] = datetime.now().isoformat()
        
        
        return await self.repo.create_user(user_dict)

    async def login_user(self, payload: OAuth2PasswordRequestForm, response: Response):
        email = payload.username
        user = await self.repo.find_by_email(email)
        
        if not user:
            raise Unauthorized("Invalid email or password")

        tokens = generate_tokens(user)
        
        await self.token.create_token(
            user_id=str(user["_id"]), 
            token_str=tokens["refresh_token"],
            days_valid=settings.refresh_expire_in_days
        )

        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,
            secure=False, 
            samesite="lax",
            max_age=(settings.refresh_expire_in_days * 24 * 60) * 60
        )
        
        return tokens
    
    async def refresh_token(self, refresh_token: str, response: Response):
        try:
            payload = jwt.decode(
                refresh_token, 
                settings.refresh_token.get_secret_value(), 
                algorithms=[settings.algorithm]
            )
        except jwt.exceptions.InvalidSignatureError:
            raise Unauthorized("Invalid refresh token signature")
        except jwt.exceptions.ExpiredSignatureError:
            raise Unauthorized("Refresh token expired")

        if payload.get("type") != "refresh":
            raise Unauthorized("This is not a refresh token")

        db_token = await self.token.find_and_revoke(refresh_token)
        if not db_token:
            raise Unauthorized("Token invalid or already used")

        user = await self.repo.find_by_email(payload.get("sub"))
        if not user:
            raise NotFound("User not found")

        new_tokens = generate_tokens(user)
        
        new_rt = new_tokens["refresh_token"] if isinstance(new_tokens, dict) else new_tokens.refresh_token

        await self.token.create_token(
            user_id=str(user["_id"]),
            token_str=new_rt,
            days_valid=settings.refresh_expire_in_days
        )

        response.set_cookie(
            key="refresh_token",
            value=new_rt,
            httponly=True,
            secure=False, 
            samesite="lax",
            max_age=(settings.refresh_expire_in_days * 24 * 60) * 60
        )

        return new_tokens




    

    async def register_admin(self, user_in: UserCreate, secret_name: SecretStr, secret_pass: SecretStr):
        if (secret_name.get_secret_value() != settings.admin_name.get_secret_value() or 
            secret_pass.get_secret_value() != settings.admin_pass.get_secret_value()):
            raise Forbidden()

        if await self.repo.find_by_email(user_in.email):
            raise BadRequest("email already exists")

        user_dict = user_in.model_dump()
        user_dict["role"] = UserRole.ADMIN.value
        user_dict["password"] = hash_password(user_in.password)
        user_dict["created_at"] = datetime.now() + timedelta(hours=5,minutes=30)

        return await self.repo.create_user(user_dict)

    async def delete_user_account(self, token: TokenResponse):
        was_deleted = await self.repo.remove_user(token.id)
        
        if not was_deleted:
            raise NotFound("User not found or already deleted")
        
        return {"message": "User successfully deleted"}