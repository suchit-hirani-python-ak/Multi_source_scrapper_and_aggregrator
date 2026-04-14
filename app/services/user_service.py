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
        # 1. Check if user exists
        if await self.repo.find_by_email(user_in.email):
            raise BadRequest("User already exists")


        # 2. Convert to dict and HASH the password
        user_dict = user_in.model_dump()
        user_dict["role"] = UserRole.USER.value
        user_dict["password"] = hash_password(user_in.password)
        
        user_dict["created_at"] = datetime.now().isoformat()
        
        
        # 4. Save to MongoDB
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
    # 1. JWT Decoding
        try:
            payload = jwt.decode(
                refresh_token, 
                settings.refresh_token.get_secret_value(), 
                algorithms=[settings.algorithm]
            )
        except jwt.exceptions.InvalidSignatureError:
            raise Unauthorized("Invalid refresh token signature")
        except jwt.exceptions.ExpiredSignatureError:
            # Important: If it's expired in JWT, it might still be in DB. 
            # You could optionally revoke it in DB here too.
            raise Unauthorized("Refresh token expired")

        if payload.get("type") != "refresh":
            raise Unauthorized("This is not a refresh token")

        # 2. Atomic Database Validation & Revocation
        db_token = await self.token.find_and_revoke(refresh_token)
        if not db_token:
            raise Unauthorized("Token invalid or already used")

        # 3. Find User
        user = await self.repo.find_by_email(payload.get("sub"))
        if not user:
            raise NotFound("User not found")

        # 4. Generate NEW tokens
        new_tokens = generate_tokens(user)
        
        # Handle both dict and Pydantic model return types
        new_rt = new_tokens["refresh_token"] if isinstance(new_tokens, dict) else new_tokens.refresh_token

        # 5. SAVE the NEW refresh token to DB
        await self.token.create_token(
            user_id=str(user["_id"]),
            token_str=new_rt,
            days_valid=settings.refresh_expire_in_days
        )

        # 6. Update the Cookie
        response.set_cookie(
            key="refresh_token",
            value=new_rt,
            httponly=True,
            secure=False, # Set to True in production (HTTPS)
            samesite="lax",
            max_age=(settings.refresh_expire_in_days * 24 * 60) * 60
        )

        return new_tokens




    

    async def register_admin(self, user_in: UserCreate, secret_name: SecretStr, secret_pass: SecretStr):
        # 1. Verify against .env secrets
        if (secret_name.get_secret_value() != settings.admin_name.get_secret_value() or 
            secret_pass.get_secret_value() != settings.admin_pass.get_secret_value()):
            raise Forbidden()

        # 2. Check if exists
        if await self.repo.find_by_email(user_in.email):
            raise BadRequest("email already exists")

        # 3. Force Admin Role
        user_dict = user_in.model_dump()
        user_dict["role"] = UserRole.ADMIN.value
        user_dict["password"] = hash_password(user_in.password)
        user_dict["created_at"] = datetime.now() + timedelta(hours=5,minutes=30)

        return await self.repo.create_user(user_dict)

    async def delete_user_account(self, token: TokenResponse):
        # 1. You MUST await the database call
        was_deleted = await self.repo.remove_user(token.id)
        
        # 2. Check the result
        if not was_deleted:
            # 3. You MUST raise the exception to stop execution
            raise NotFound("User not found or already deleted")
        
        # This will only be reached if was_deleted is True
        return {"message": "User successfully deleted"}