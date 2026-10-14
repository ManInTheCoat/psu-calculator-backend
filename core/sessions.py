"""Сессии пользователей в Redis.

При входе создаётся сессия: случайный session_id (uuid4) отдаётся браузеру в куке,
а в Redis записывается

    session:<session_id>  ->  {"user_id": 1, "login": "builder"}

со сроком жизни SESSION_TTL_SECONDS.
"""

import json
import uuid

from redis.asyncio import Redis

from core.config import settings

SESSION_KEY_PREFIX = "session:"

redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)


def _key(session_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{session_id}"


async def create_session(user_id: int, login: str) -> str:
    """Создаёт сессию и возвращает её session_id."""
    session_id = str(uuid.uuid4())
    value = json.dumps({"user_id": user_id, "login": login})
    await redis_client.set(_key(session_id), value, ex=settings.SESSION_TTL_SECONDS)
    return session_id


async def get_session(session_id: str) -> dict | None:
    """Данные сессии {"user_id", "login"} или None, если сессии нет или она истекла."""
    value = await redis_client.get(_key(session_id))
    return json.loads(value) if value else None


async def delete_session(session_id: str) -> None:
    """Удаляет сессию (выход)."""
    await redis_client.delete(_key(session_id))
