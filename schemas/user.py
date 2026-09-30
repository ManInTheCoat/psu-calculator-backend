"""Сериализаторы пользователей."""

from pydantic import BaseModel, ConfigDict, Field


class UserSerializer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str


class UserRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$", examples=["new_builder"])
    password: str = Field(min_length=6, max_length=128, examples=["builder123"])


class UserLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login: str = Field(min_length=1, max_length=50, examples=["new_builder"])
    password: str = Field(min_length=1, max_length=128, examples=["builder123"])
