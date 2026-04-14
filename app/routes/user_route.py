from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Header, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import SecretStr
from app.db.session import get_db
from app.schemas.refresh import RefreshResponse
from app.schemas.users import UserCreate, UserResponse
from app.schemas.token import Token
from app.dependencies.dependency import get_current_user
from app.core.config import settings
from app.services.user_service import UserService

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate, db = Depends(get_db))->dict:
    """providing email and password provides output as registerd user

    Args:
        user_in (UserCreate): get pydantic data
        db (_type_, optional): connection with db using get_db

    Returns:
        dict: shows confirmation that user registered successfully 
    """
    return await UserService(db).register_user(user_in)


@router.post("/login",response_model=Token)
async def login(response:Response,
    payload: Annotated[OAuth2PasswordRequestForm, Depends()],
    db = Depends(get_db)):
    """provide username and password make sure you are registered before

    Args:
        response (Response): gets response
        payload (Annotated[OAuth2PasswordRequestForm, Depends): gives login form
        db (_type_, optional): connection with db using get_db

    Returns:
        dict: provide tokens as response
    """
    return await UserService(db).login_user(payload,response)

@router.post("/refresh",response_model=Token)
async def refresh(response: Response,refresh_token:str,db = Depends(get_db))->dict:
    """by providing refresh token generate pairs of tokens

    Args:
        refresh_token (str): give refresh token as query parameter
        db (_type_, optional): connect db by using get_db

    Returns:
        dict: return tokens
    """
    return await UserService(db).refresh_token(refresh_token,response)

@router.post("/setup-root",response_model=UserResponse)
async def setup_admin(
    user: UserCreate,
    db = Depends(get_db),
    x_admin_user: SecretStr = Header(...),
    x_admin_pass: SecretStr = Header(...)
):
    """can able to create new admin from this route

    Args:
        user (UserCreate): get data from pydantic
        db (_type_, optional): connection with db using get_db
        x_admin_user (str, optional): get from env file
        x_admin_pass (str, optional): get from env file

    Returns:
        dict: return new admin 
    """
    return await UserService(db).register_admin(user, x_admin_user, x_admin_pass)

@router.delete("/delete")
async def delete(
    token=Depends(get_current_user),     
    db=Depends(get_db),
)->dict:
    """can delete user

    Args:
        token (_type_, optional): by token get current_user
        db (_type_, optional): connection with db using get_db

    Returns:
        dict: return user deleted
    """
    return await UserService(db).delete_user_account(token)