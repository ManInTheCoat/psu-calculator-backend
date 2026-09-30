"""Веб-сервис. Домен компонентов ПК (услуги): /api/power_components

    GET    /api/power_components?max_power=...        список опубликованных с фильтром по мощности
    GET    /api/power_components/feed                  лента без ид (первый опубликованный)
    GET    /api/power_components/feed/{id}?next=true   лента по ид / следующий после ид
    GET    /api/power_components/draft                 черновик текущего пользователя
    POST   /api/power_components                       создание черновика + фото и видео в MinIO
    PUT    /api/power_components/{id}/publish          публикация черновика (draft -> published)
    DELETE /api/power_components/{id}                  логическое удаление (-> deleted)
    POST   /api/power_components/{id}/like             лайк: 1 — поставить, 0 — отменить

Текущий пользователь во всех методах берётся из singleton get_current_user().
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile, status
from sqlalchemy import delete, exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from core.current_user import CurrentUser, get_current_user
from db.session import get_db
from models.power_component import PowerComponent
from models.power_component_like import PowerComponentLike
from models.user import User
from schemas.common import ERROR_RESPONSES, ApiResponse
from schemas.power_component import (
    POWER_MAX,
    POWER_MIN,
    PowerComponentDeletedSerializer,
    PowerComponentFeedSerializer,
    PowerComponentLikeRequest,
    PowerComponentLikeSerializer,
    PowerComponentListItemSerializer,
    PowerComponentPublishRequest,
    PowerComponentSerializer,
)
from services.minio_storage import (
    MAX_IMAGE_SIZE,
    MAX_VIDEO_SIZE,
    detect_image,
    detect_video,
    generate_object_name,
    storage,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/power_components", tags=["power_components"])

INT32_MAX = 2_147_483_647
PowerComponentId = Annotated[int, Path(ge=1, le=INT32_MAX, description="ID компонента")]


# ---------- вспомогательные функции ----------

def _likes_count_expr():
    """Подзапрос: количество лайков компонента."""
    return (
        select(func.count(PowerComponentLike.id))
        .where(PowerComponentLike.power_component_id == PowerComponent.id)
        .correlate(PowerComponent)
        .scalar_subquery()
    )


def _is_liked_expr(user_id: int):
    """Подзапрос: поставил ли пользователь лайк компоненту."""
    return exists().where(
        PowerComponentLike.power_component_id == PowerComponent.id,
        PowerComponentLike.user_id == user_id,
    )


async def _get_active_component(db: AsyncSession, power_component_id: int) -> PowerComponent:
    """Компонент в статусе draft/published, иначе 404."""
    stmt = select(PowerComponent).where(
        PowerComponent.id == power_component_id,
        PowerComponent.status != "deleted",
    )
    component = (await db.execute(stmt)).scalar_one_or_none()
    if component is None:
        raise HTTPException(status_code=404, detail=f"Компонент с id={power_component_id} не найден")
    return component


async def _read_upload(upload: UploadFile | None, kind: str) -> tuple[bytes, str, str] | None:
    """Читает и проверяет файл из формы. Возвращает (данные, content_type, расширение)."""
    if upload is None or not upload.filename:
        return None

    data = await upload.read()
    if not data:
        return None

    if kind == "image":
        max_size, detected, human = MAX_IMAGE_SIZE, detect_image(data[:16]), "изображением PNG, JPEG, GIF или WEBP"
    else:
        max_size, detected, human = MAX_VIDEO_SIZE, detect_video(data[:16]), "видео MP4, MOV или WEBM"

    if len(data) > max_size:
        raise HTTPException(status_code=400, detail=f"Файл {kind} больше {max_size // (1024 * 1024)} МБ")
    if detected is None:
        raise HTTPException(status_code=400, detail=f"Файл {kind} должен быть {human}")

    content_type, extension = detected
    return data, content_type, extension


async def _get_feed_item(db: AsyncSession, power_component_id: int, user: CurrentUser) -> PowerComponentFeedSerializer:
    stmt = (
        select(
            PowerComponent,
            _likes_count_expr().label("likes_count"),
            _is_liked_expr(user.id).label("is_liked"),
        )
        .options(selectinload(PowerComponent.creator))
        .where(PowerComponent.id == power_component_id, PowerComponent.status == "published")
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Опубликованный компонент с id={power_component_id} не найден")

    component, likes_count, is_liked = row
    return PowerComponentFeedSerializer(
        id=component.id,
        title=component.title,
        description=component.description,
        image_url=component.image_url,
        video_url=component.video_url,
        power_watt=component.power_watt,
        weight_gram=component.weight_gram,
        formed_at=component.formed_at,
        creator=component.creator,
        likes_count=likes_count,
        is_liked=int(is_liked),
        is_mine=int(component.creator_id == user.id),
    )


async def _first_published_id(db: AsyncSession, after_id: int = 0) -> int | None:
    stmt = (
        select(PowerComponent.id)
        .where(PowerComponent.status == "published", PowerComponent.id > after_id)
        .order_by(PowerComponent.id)
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


# ---------- методы ----------

@router.get(
    "",
    summary="Список опубликованных компонентов с фильтрацией по мощности",
    response_model=ApiResponse[list[PowerComponentListItemSerializer]],
    responses={400: ERROR_RESPONSES[400]},
)
async def get_power_components(
    max_power: int | None = Query(default=None, ge=POWER_MIN, le=POWER_MAX, description="Мощность до, Вт"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    stmt = (
        select(PowerComponent, _likes_count_expr().label("likes_count"))
        .where(PowerComponent.status == "published")
        .order_by(PowerComponent.id)
    )
    if max_power is not None:
        stmt = stmt.where(PowerComponent.power_watt <= max_power)

    rows = (await db.execute(stmt)).all()
    items = [
        PowerComponentListItemSerializer(
            id=component.id,
            title=component.title,
            image_url=component.image_url,
            power_watt=component.power_watt,
            weight_gram=component.weight_gram,
            likes_count=likes_count,
            is_mine=int(component.creator_id == user.id),
        )
        for component, likes_count in rows
    ]
    return ApiResponse(data=items)


@router.get(
    "/feed",
    summary="Лента без ид: первый опубликованный компонент",
    response_model=ApiResponse[PowerComponentFeedSerializer],
    responses={404: ERROR_RESPONSES[404]},
)
async def get_power_component_feed_first(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    first_id = await _first_published_id(db)
    if first_id is None:
        raise HTTPException(status_code=404, detail="Нет опубликованных компонентов")
    return ApiResponse(data=await _get_feed_item(db, first_id, user))


@router.get(
    "/feed/{power_component_id}",
    summary="Лента по ид; с ?next=true — следующий опубликованный после ид",
    response_model=ApiResponse[PowerComponentFeedSerializer],
    responses={400: ERROR_RESPONSES[400], 404: ERROR_RESPONSES[404]},
)
async def get_power_component_feed(
    power_component_id: PowerComponentId,
    is_next: bool = Query(default=False, alias="next"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if is_next:
        next_id = await _first_published_id(db, after_id=power_component_id)
        if next_id is None:
            next_id = await _first_published_id(db)
        if next_id is None:
            raise HTTPException(status_code=404, detail="Нет опубликованных компонентов")
        power_component_id = next_id

    return ApiResponse(data=await _get_feed_item(db, power_component_id, user))


@router.get(
    "/draft",
    summary="Черновик текущего пользователя",
    response_model=ApiResponse[PowerComponentSerializer],
    responses={404: ERROR_RESPONSES[404]},
)
async def get_power_component_draft(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    stmt = select(PowerComponent).where(
        PowerComponent.creator_id == user.id,
        PowerComponent.status == "draft",
    )
    draft = (await db.execute(stmt)).scalar_one_or_none()
    if draft is None:
        raise HTTPException(status_code=404, detail="У пользователя нет черновика")
    return ApiResponse(data=PowerComponentSerializer.model_validate(draft))


@router.post(
    "",
    summary="Создание черновика с фото и видео (multipart/form-data)",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[PowerComponentSerializer],
    responses={400: ERROR_RESPONSES[400], 409: ERROR_RESPONSES[409], 500: ERROR_RESPONSES[500]},
)
async def create_power_component(
    title: str = Form(min_length=1, max_length=100, description="Название компонента"),
    image: UploadFile | None = File(default=None, description="Фото: PNG, JPEG, GIF, WEBP до 5 МБ"),
    video: UploadFile | None = File(default=None, description="Короткое видео: MP4, MOV, WEBM до 50 МБ"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    title = title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Название не может быть пустым")

    existing = (
        await db.execute(
            select(PowerComponent.id).where(
                PowerComponent.creator_id == user.id,
                PowerComponent.status == "draft",
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"У пользователя уже есть черновик id={existing}: опубликуйте или удалите его",
        )

    image_file = await _read_upload(image, "image")
    video_file = await _read_upload(video, "video")

    component = PowerComponent(
        title=title,
        status="draft",
        image_url="",
        video_url="",
        creator_id=user.id,
    )
    db.add(component)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="У пользователя уже есть черновик")

    uploaded: list[str] = []
    try:
        for kind, file in (("image", image_file), ("video", video_file)):
            if file is None:
                continue
            data, content_type, extension = file
            object_name = generate_object_name(component.id, kind, extension)
            url = await run_in_threadpool(storage.upload, object_name, data, content_type)
            uploaded.append(object_name)
            setattr(component, f"{kind}_url", url)

        await db.commit()
    except Exception as exc:
        await db.rollback()
        for object_name in uploaded:
            try:
                await run_in_threadpool(storage.remove, object_name)
            except Exception:
                logger.exception("Не удалось удалить %s из MinIO", object_name)
        logger.exception("Ошибка создания компонента")
        raise HTTPException(status_code=500, detail=f"Не удалось сохранить компонент: {exc}") from exc

    await db.refresh(component)
    return ApiResponse(message="Черновик создан", data=PowerComponentSerializer.model_validate(component))


@router.put(
    "/{power_component_id}/publish",
    summary="Публикация черновика: draft -> published",
    response_model=ApiResponse[PowerComponentSerializer],
    responses={k: ERROR_RESPONSES[k] for k in (400, 403, 404, 409)},
)
async def publish_power_component(
    power_component_id: PowerComponentId,
    body: PowerComponentPublishRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    component = await _get_active_component(db, power_component_id)

    if component.creator_id != user.id:
        raise HTTPException(status_code=403, detail="Опубликовать можно только свой компонент")
    if component.status != "draft":
        raise HTTPException(status_code=409, detail="Опубликовать можно только черновик")

    component.description = body.description.strip()
    component.power_watt = body.power_watt
    component.weight_gram = body.weight_gram
    component.status = "published"
    component.formed_at = func.now()

    await db.commit()
    await db.refresh(component)
    return ApiResponse(message="Компонент опубликован", data=PowerComponentSerializer.model_validate(component))


@router.delete(
    "/{power_component_id}",
    summary="Логическое удаление своего компонента (статус deleted)",
    response_model=ApiResponse[PowerComponentDeletedSerializer],
    responses={k: ERROR_RESPONSES[k] for k in (400, 403, 404)},
)
async def delete_power_component(
    power_component_id: PowerComponentId,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    component = await _get_active_component(db, power_component_id)

    if component.creator_id != user.id:
        raise HTTPException(status_code=403, detail="Удалить можно только свой компонент")

    component.status = "deleted"
    await db.commit()

    return ApiResponse(
        message="Компонент удалён",
        data=PowerComponentDeletedSerializer(id=component.id, status=component.status),
    )


@router.post(
    "/{power_component_id}/like",
    summary="Лайк от текущего пользователя: like=1 ставит, like=0 отменяет",
    response_model=ApiResponse[PowerComponentLikeSerializer],
    responses={k: ERROR_RESPONSES[k] for k in (400, 404)},
)
async def like_power_component(
    power_component_id: PowerComponentId,
    body: PowerComponentLikeRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    component = await _get_active_component(db, power_component_id)
    if component.status != "published":
        raise HTTPException(status_code=404, detail=f"Опубликованный компонент с id={power_component_id} не найден")

    liked_stmt = select(PowerComponentLike.id).where(
        PowerComponentLike.power_component_id == component.id,
        PowerComponentLike.user_id == user.id,
    )
    already_liked = (await db.execute(liked_stmt)).scalar_one_or_none() is not None

    if body.like == 1 and not already_liked:
        db.add(PowerComponentLike(user_id=user.id, power_component_id=component.id))
    elif body.like == 0 and already_liked:
        await db.execute(
            delete(PowerComponentLike).where(
                PowerComponentLike.power_component_id == component.id,
                PowerComponentLike.user_id == user.id,
            )
        )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()

    likes_count = (
        await db.execute(
            select(func.count(PowerComponentLike.id)).where(PowerComponentLike.power_component_id == component.id)
        )
    ).scalar_one()

    return ApiResponse(
        message="Лайк поставлен" if body.like == 1 else "Лайк отменён",
        data=PowerComponentLikeSerializer(
            power_component_id=component.id,
            is_liked=body.like,
            likes_count=likes_count,
        ),
    )
