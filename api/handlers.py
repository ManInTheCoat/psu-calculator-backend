"""Обработчики запросов приложения.

Шесть HTTP-методов:
    GET  /power_components                    — плитка с фильтрацией по мощности
    GET  /power_components/feed                — лента, первая опубликованная карточка
    GET  /power_components/feed/{id}           — лента, карточка компонента (?next=true — следующая)
    GET  /power_components/draft                — страница добавления, черновик текущего пользователя
    POST /power_components/draft                — создание черновика
    POST /power_components/{id}/publish         — публикация черновика
    POST /power_components/{id}/delete          — логическое удаление через SQL UPDATE
"""

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.power_component import PowerComponent
from models.user import User
from models.power_component_like import PowerComponentLike

router = APIRouter()
templates = Jinja2Templates(directory="templates")

POWER_MIN = 0
POWER_MAX = 500
POWER_STEP = 10

CURRENT_USER_ID = 1


@router.get("/")
@router.get("/power_components")
async def get_power_components_tile(
    request: Request,
    max_power: int | None = Query(default=None, ge=POWER_MIN, le=POWER_MAX),
    db: AsyncSession = Depends(get_db),
):
    """Плитка: каталог опубликованных компонентов с количеством лайков."""
    current_max_power = POWER_MAX if max_power is None else max_power

    likes_count = func.count(PowerComponentLike.id).label("likes_count")
    stmt = (
        select(PowerComponent, likes_count)
        .outerjoin(PowerComponentLike, PowerComponentLike.power_component_id == PowerComponent.id)
        .where(PowerComponent.status == "published")
        .where(PowerComponent.power_watt <= current_max_power)
        .group_by(PowerComponent.id)
        .order_by(PowerComponent.id)
    )
    result = await db.execute(stmt)

    tile_power_components = []
    for component, count in result.all():
        tile_power_components.append({"component": component, "likes_count": count})

    return templates.TemplateResponse(
        request=request,
        name="tile.html",
        context={
            "power_components": tile_power_components,
            "max_power": current_max_power,
            "power_min": POWER_MIN,
            "power_max": POWER_MAX,
            "power_step": POWER_STEP,
        },
    )


async def _get_component_with_likes(db: AsyncSession, power_component_id: int):
    """Опубликованный компонент по ID вместе с количеством лайков, либо None."""
    likes_count = func.count(PowerComponentLike.id).label("likes_count")
    stmt = (
        select(PowerComponent, likes_count)
        .outerjoin(PowerComponentLike, PowerComponentLike.power_component_id == PowerComponent.id)
        .where(PowerComponent.id == power_component_id, PowerComponent.status == "published")
        .group_by(PowerComponent.id)
    )
    result = await db.execute(stmt)
    return result.first()


@router.get("/power_components/feed")
async def get_power_component_feed_first(request: Request, db: AsyncSession = Depends(get_db)):
    """Лента без ID: открывает первую опубликованную карточку (для панели вкладок)."""
    stmt = (
        select(PowerComponent.id)
        .where(PowerComponent.status == "published")
        .order_by(PowerComponent.id)
        .limit(1)
    )
    result = await db.execute(stmt)
    first_id = result.scalar_one_or_none()

    if first_id is None:
        raise HTTPException(status_code=404, detail="Нет опубликованных компонентов")

    return await get_power_component_feed(request, first_id, is_next=False, db=db)


@router.get("/power_components/feed/{power_component_id}")
async def get_power_component_feed(
    request: Request,
    power_component_id: int,
    is_next: bool = Query(default=False, alias="next"),
    db: AsyncSession = Depends(get_db),
):
    """Лента: карточка компонента с автовоспроизводимым видео."""
    if is_next:
        stmt = (
            select(PowerComponent.id)
            .where(PowerComponent.status == "published", PowerComponent.id > power_component_id)
            .order_by(PowerComponent.id)
            .limit(1)
        )
        result = await db.execute(stmt)
        next_id = result.scalar_one_or_none()

        if next_id is None:
            stmt = (
                select(PowerComponent.id)
                .where(PowerComponent.status == "published")
                .order_by(PowerComponent.id)
                .limit(1)
            )
            result = await db.execute(stmt)
            next_id = result.scalar_one_or_none()

        if next_id is None:
            raise HTTPException(status_code=404, detail="Нет опубликованных компонентов")

        power_component_id = next_id

    row = await _get_component_with_likes(db, power_component_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Компонент не найден")

    component, likes_count = row

    return templates.TemplateResponse(
        request=request,
        name="feed.html",
        context={"power_component": component, "likes_count": likes_count},
    )


@router.get("/power_components/draft")
async def get_power_component_draft(request: Request, db: AsyncSession = Depends(get_db)):
    """Добавление: черновик текущего пользователя, либо пустая форма."""
    stmt = select(PowerComponent).where(
        PowerComponent.creator_id == CURRENT_USER_ID,
        PowerComponent.status == "draft",
    )
    result = await db.execute(stmt)
    draft = result.scalar_one_or_none()

    return templates.TemplateResponse(
        request=request,
        name="add.html",
        context={"power_component": draft},
    )

@router.post("/power_components/draft")
async def create_power_component_draft(
    title: str = Form(...),
    image_url: str | None = Form(default=None),
    video_url: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Кнопка «Далее»: создаёт черновик текущего пользователя."""
    stmt = select(PowerComponent).where(
        PowerComponent.creator_id == CURRENT_USER_ID,
        PowerComponent.status == "draft",
    )
    result = await db.execute(stmt)
    draft = result.scalar_one_or_none()

    if draft is None:
        draft = PowerComponent(
            title=title,
            image_url=image_url or None,
            video_url=video_url or None,
            status="draft",
            creator_id=CURRENT_USER_ID,
        )
        db.add(draft)
    else:
        draft.title = title
        draft.image_url = image_url or draft.image_url
        draft.video_url = video_url or draft.video_url

    await db.commit()

    return RedirectResponse(url="/power_components/draft", status_code=303)


@router.post("/power_components/{power_component_id}/publish")
async def publish_power_component(
    power_component_id: int,
    description: str = Form(...),
    power_watt: int = Form(...),
    weight_gram: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Кнопка «Опубликовать»: дозаполняет черновик и переводит в статус published."""
    stmt = select(PowerComponent).where(
        PowerComponent.id == power_component_id,
        PowerComponent.creator_id == CURRENT_USER_ID,
        PowerComponent.status == "draft",
    )
    result = await db.execute(stmt)
    draft = result.scalar_one_or_none()

    if draft is None:
        raise HTTPException(status_code=404, detail="Черновик не найден")

    draft.description = description
    draft.power_watt = power_watt
    draft.weight_gram = weight_gram
    draft.status = "published"
    draft.formed_at = func.now()

    await db.commit()

    return RedirectResponse(url="/power_components", status_code=303)

@router.post("/power_components/{power_component_id}/delete")
async def delete_power_component(power_component_id: int, db: AsyncSession = Depends(get_db)):
    """Логическое удаление: статус меняется на deleted через сырой SQL UPDATE."""
    stmt = text(
        "UPDATE power_components SET status = 'deleted' "
        "WHERE id = :id AND status = 'published'"
    )
    await db.execute(stmt, {"id": power_component_id})
    await db.commit()

    return RedirectResponse(url="/power_components", status_code=303)
