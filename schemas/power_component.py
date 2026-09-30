"""Сериализаторы (Pydantic-схемы) компонентов ПК."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from schemas.user import UserSerializer

POWER_MIN = 0
POWER_MAX = 500


# ---------- ответы ----------

class PowerComponentListItemSerializer(BaseModel):
    """Карточка в плитке (списке)."""

    id: int
    title: str
    image_url: str
    power_watt: int | None
    weight_gram: int | None
    likes_count: int
    is_mine: int = Field(description="1 — создатель компонента совпадает с текущим пользователем, иначе 0")


class PowerComponentSerializer(BaseModel):
    """Компонент со всеми полями таблицы power_components (черновик, публикация)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: str
    image_url: str
    video_url: str
    power_watt: int | None
    weight_gram: int | None
    created_at: datetime
    formed_at: datetime | None
    creator_id: int


class PowerComponentFeedSerializer(BaseModel):
    """Карточка ленты: вложенная сериализация создателя (creator)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    image_url: str
    video_url: str
    power_watt: int | None
    weight_gram: int | None
    formed_at: datetime | None
    creator: UserSerializer
    likes_count: int
    is_liked: int = Field(description="1 — текущий пользователь поставил лайк, иначе 0")
    is_mine: int = Field(description="1 — компонент создан текущим пользователем, иначе 0")


class PowerComponentLikeSerializer(BaseModel):
    power_component_id: int
    is_liked: int
    likes_count: int


class PowerComponentDeletedSerializer(BaseModel):
    id: int
    status: str


# ---------- запросы ----------

class PowerComponentPublishRequest(BaseModel):
    """Тело PUT публикации: дозаполнение черновика полями по теме."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=500, examples=["Видеокарта среднего класса"])
    power_watt: int = Field(gt=POWER_MIN, le=POWER_MAX, description="Потребляемая мощность, Вт", examples=[220])
    weight_gram: int = Field(gt=0, le=100_000, description="Вес, г", examples=[1100])


class PowerComponentLikeRequest(BaseModel):
    """Тело POST лайка: 1 — поставить лайк, 0 — отменить."""

    model_config = ConfigDict(extra="forbid")

    like: Annotated[int, Field(ge=0, le=1, strict=True, examples=[1])]
