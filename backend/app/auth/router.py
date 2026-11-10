from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.schemas import Token, UserCreate, UserPublic
from app.core.security import create_access_token, hash_password, verify_password
from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, session: Session) -> User:
    email = str(body.email).casefold()
    hashed_password = await run_in_threadpool(hash_password, body.password)
    user = User(
        email=email,
        hashed_password=hashed_password,
        display_name=body.display_name,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from exc
    return user


@router.post("/login", response_model=Token)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], session: Session) -> Token:
    email = form.username.casefold()
    user = await session.scalar(select(User).where(User.email == email))
    if user is None or not await run_in_threadpool(
        verify_password, form.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.email))


@router.get("/me", response_model=UserPublic)
async def read_me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user
