"""Единый JSON-формат ошибок для методов /api:

    {"status": "fail", "message": "..."}

Ошибки валидации (неверный тип, лишние/системные поля, id вне диапазона)
возвращаются с кодом 400.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def _is_api(request: Request) -> bool:
    return request.url.path.startswith("/api")


def _fail(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"status": "fail", "message": message})


def _validation_message(exc: RequestValidationError) -> str:
    parts = []
    for error in exc.errors():
        location = ".".join(str(item) for item in error.get("loc", ()) if item != "body")
        message = error.get("msg", "")
        if error.get("type") == "extra_forbidden":
            message = "поле нельзя передавать с клиента"
        elif "Expected UploadFile" in message:
            message = "ожидается файл, а не текст"
        parts.append(f"{location}: {message}" if location else message)
    return "; ".join(parts) or "Некорректный запрос"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        if not _is_api(request):
            return await http_exception_handler(request, exc)
        messages = {404: "Метод не найден", 405: "HTTP-метод не поддерживается"}
        detail = exc.detail if exc.detail not in ("Not Found", "Method Not Allowed") else messages.get(exc.status_code)
        return _fail(exc.status_code, str(detail))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        if not _is_api(request):
            return await request_validation_exception_handler(request, exc)
        return _fail(400, _validation_message(exc))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.exception("Необработанная ошибка: %s %s", request.method, request.url.path)
        return _fail(500, "Внутренняя ошибка сервера")
