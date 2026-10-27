"""Общие схемы ответов API.

Успешный ответ - сами данные (объект или массив) без обёрток,
результат передаётся HTTP-кодом ответа (200, 201, 204).
Ошибка - HTTP-код 4xx/5xx и стандартное для FastAPI тело {"detail": "..."}.
"""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    detail: str


ERROR_RESPONSES = {
    400: {"model": ErrorDetail, "description": "Некорректный запрос"},
    401: {"model": ErrorDetail, "description": "Требуется авторизация"},
    403: {"model": ErrorDetail, "description": "Нет прав на действие"},
    404: {"model": ErrorDetail, "description": "Не найдено"},
    409: {"model": ErrorDetail, "description": "Конфликт с текущим состоянием"},
    500: {"model": ErrorDetail, "description": "Внутренняя ошибка сервера"},
}
