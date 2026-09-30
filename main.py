"""Точка входа приложения.

Запуск: python main.py
HTML-страницы (ЛР2):  http://127.0.0.1:8000/power_components
Веб-сервис (ЛР3):     http://127.0.0.1:8000/api/...
Swagger:              http://127.0.0.1:8000/docs
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from api.errors import register_error_handlers
from api.handlers import router as pages_router
from api.power_components_api import router as power_components_router
from api.users_api import router as users_router
from services.minio_storage import storage

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await run_in_threadpool(storage.ensure_bucket)
    except Exception as exc:
        logger.warning("MinIO недоступен: %s", exc)
    yield


app = FastAPI(title="PC Power Calc", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
register_error_handlers(app)

app.include_router(power_components_router)
app.include_router(users_router)
app.include_router(pages_router, include_in_schema=False)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
