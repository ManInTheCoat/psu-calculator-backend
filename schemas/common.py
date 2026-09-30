"""Общий формат ответов API.

Успех:  {"status": "success", "message": "...", "data": {...}}
Ошибка: {"status": "fail", "message": "..."}
"""

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    status: Literal["success"] = "success"
    message: str | None = None
    data: T | None = None


class FailResponse(BaseModel):
    status: Literal["fail"] = "fail"
    message: str


ERROR_RESPONSES = {
    400: {"model": FailResponse, "description": "Некорректный запрос"},
    403: {"model": FailResponse, "description": "Нет прав на действие"},
    404: {"model": FailResponse, "description": "Не найдено"},
    409: {"model": FailResponse, "description": "Конфликт с текущим состоянием"},
    500: {"model": FailResponse, "description": "Внутренняя ошибка сервера"},
}
