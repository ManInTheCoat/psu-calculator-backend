"""Текущий пользователь-создатель."""

CREATOR_ID = 1


class CurrentUser:
    """Singleton: единственный экземпляр текущего пользователя."""

    _instance: "CurrentUser | None" = None

    id: int

    def __new__(cls) -> "CurrentUser":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance.id = CREATOR_ID
            cls._instance = instance
        return cls._instance


def get_current_user() -> CurrentUser:
    """Зависимость FastAPI: текущий пользователь (всегда один и тот же объект)."""
    return CurrentUser()
