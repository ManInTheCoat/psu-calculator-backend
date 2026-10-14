"""Текущий пользователь по сессии.

Кука session_id -> сессия в Redis -> пользователь. Две зависимости FastAPI:

    get_current_user_optional  гость или пользователь: для методов чтения
                               (список и лента), гостю возвращается None
    get_current_user           только авторизованный пользователь: для методов
                               создателя; без действующей сессии ответ 401
"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyCookie

from core.config import settings
from core.sessions import get_session

session_cookie = APIKeyCookie(
    name=settings.SESSION_COOKIE_NAME,
    auto_error=False,
    description="Кука сессии: выдаётся методом POST /api/users/login",
)


@dataclass(frozen=True)
class CurrentUser:
    id: int
    login: str
    session_id: str


async def _user_by_session(session_id: str | None) -> CurrentUser | None:
    if not session_id:
        return None
    data = await get_session(session_id)
    if data is None:
        return None
    return CurrentUser(id=data["user_id"], login=data["login"], session_id=session_id)


async def get_current_user_optional(request: Request) -> CurrentUser | None:
    """Пользователь по куке или None для гостя."""
    return await _user_by_session(request.cookies.get(settings.SESSION_COOKIE_NAME))


async def get_current_user(session_id: str | None = Depends(session_cookie)) -> CurrentUser:
    """Авторизованный пользователь; без действующей сессии — 401."""
    user = await _user_by_session(session_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация")
    return user
