"""Веб-сервис. Домен пользователей: /api/users

    POST /api/users/register   регистрация
    POST /api/users/login      аутентификация (заглушка)
    POST /api/users/logout     деавторизация (заглушка)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.current_user import CurrentUser, get_current_user
from core.security import hash_password
from db.session import get_db
from models.user import User
from schemas.common import ERROR_RESPONSES, ApiResponse
from schemas.user import UserLoginRequest, UserRegisterRequest, UserSerializer

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post(
    "/register",
    summary="Регистрация нового пользователя",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[UserSerializer],
    responses={400: ERROR_RESPONSES[400], 409: ERROR_RESPONSES[409]},
)
async def register_user(body: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(select(User.id).where(User.login == body.login))).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status_code=409, detail=f"Логин {body.login} уже занят")

    user = User(login=body.login, password=hash_password(body.password))
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"Логин {body.login} уже занят")

    await db.refresh(user)
    return ApiResponse(message="Пользователь зарегистрирован", data=UserSerializer.model_validate(user))


@router.post(
    "/login",
    summary="Аутентификация (заглушка: вернёт текущего пользователя-константу)",
    response_model=ApiResponse[UserSerializer],
    responses={400: ERROR_RESPONSES[400]},
)
async def login_user(
    body: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    # Заглушка
    user = await db.get(User, current_user.id)
    return ApiResponse(
        message="Заглушка",
        data=UserSerializer.model_validate(user) if user else None,
    )


@router.post(
    "/logout",
    summary="Деавторизация (заглушка)",
    response_model=ApiResponse[None],
)
async def logout_user():
    return ApiResponse(message="Заглушка")
