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
        
        # 3. Add timestamps
        user_dict["created_at"] = datetime.now().isoformat()
        
        
        # 4. Save to MongoDB
        return await self.repo.create_user(user_dict)

    async def login_user(self, payload: OAuth2PasswordRequestForm, response: Response):
            email = payload.username
            lockout_key = f"lockout:{email}"
            attempts_key = f"attempts:{email}"

            # 1. Check if user is currently locked out
            if await redis_client.exists(lockout_key):
                ttl = await redis_client.ttl(lockout_key)
                raise Forbidden(f"Account locked try again in {ttl//60} minutes")

            user = await self.repo.find_by_email(email)
            
            # 2. Verify Credentials
            if not user or not verify_password(payload.password, user.get("password")):
                # --- FAILURE BLOCK ---
                failed_count = await redis_client.incr(attempts_key)
                
                if failed_count == 1:
                    await redis_client.expire(attempts_key, 600) # 10 min window

                if failed_count >= 5:
                    await redis_client.setex(lockout_key, 600, "locked")
                    await redis_client.delete(attempts_key)
                    raise Forbidden("Too many attempts. Locked for 10 min.")
                    
                raise Unauthorized(f"Invalid credentials. {5 - failed_count} attempts left.")
            
            

            
            await redis_client.delete(attempts_key)

            tokens = generate_tokens(user)
            response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,
            secure=False, 
            samesite="lax",
            max_age=(settings.refresh_expire_in_days* 24 * 60 + 330) * 60
        )
        
            return tokens
        
    async def refresh_token(self, refresh_token: str):
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

        db_token = await self.token.get_refresh_token(refresh_token)
        
        if not db_token:
            raise Unauthorized("Refresh token not found in database")
        
        if db_token.get("revoked"):
            raise Unauthorized("This token has been revoked")

        # 2. Basic Payload Validation
        if payload.get("type") != "refresh":
            raise Unauthorized("This is not a refresh token")

        email = payload.get("sub")
        if not email:
            raise Unauthorized("Token payload missing email")

        # 3. User Validation
        user = await self.repo.find_by_email(email)
        if not user:
            raise NotFound("User not found")
                
        await self.token.revoke_token(refresh_token)
        
        return generate_tokens(user)

    

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