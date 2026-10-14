"""Веб-сервис. Домен пользователей: /api/users

    POST /api/users/register   регистрация
    POST /api/users/login      аутентификация: создаёт сессию в Redis и ставит куку session_id
    POST /api/users/logout     деавторизация: удаляет сессию из Redis и куку

Ответ — сами данные без обёрток, результат передаётся HTTP-кодом.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.current_user import CurrentUser, get_current_user, get_current_user_optional
from core.security import hash_password, verify_password
from core.sessions import create_session, delete_session
from db.session import get_db
from models.user import User
from schemas.common import ERROR_RESPONSES
from schemas.user import UserLoginRequest, UserRegisterRequest, UserSerializer

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post(
    "/register",
    summary="Регистрация нового пользователя",
    status_code=status.HTTP_201_CREATED,
    response_model=UserSerializer,
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
    return UserSerializer.model_validate(user)


@router.post(
    "/login",
    summary="Аутентификация: создаёт сессию в Redis и ставит куку session_id",
    response_model=UserSerializer,
    responses={400: ERROR_RESPONSES[400], 401: ERROR_RESPONSES[401]},
)
async def login_user(
    body: UserLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    previous: CurrentUser | None = Depends(get_current_user_optional),
):
    user = (await db.execute(select(User).where(User.login == body.login))).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    if previous is not None:
        await delete_session(previous.session_id)

    session_id = await create_session(user.id, user.login)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_id,
        max_age=settings.SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
    )
    return UserSerializer.model_validate(user)


@router.post(
    "/logout",
    summary="Деавторизация: удаляет сессию из Redis и куку",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={401: ERROR_RESPONSES[401]},
)
async def logout_user(user: CurrentUser = Depends(get_current_user)):
    await delete_session(user.session_id)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME, httponly=True, samesite="lax")
    return response
