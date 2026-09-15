"""Обработчики запросов приложения.

Три GET-метода:
    GET /power_components                   — плитка (каталог) с фильтрацией по мощности
    GET /power_components/feed/{id}         — лента, карточка одного компонента
    GET /power_components/draft             — страница добавления, отображает черновик
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates

from data.collections import power_components

router = APIRouter()
templates = Jinja2Templates(directory="templates")

POWER_MIN = 0
POWER_MAX = 500
POWER_STEP = 10


def get_published_power_components():
    """Опубликованные компоненты. Черновики и удалённые не попадают в выборку."""
    return [c for c in power_components if c["status"] == "опубликован"]


def with_likes_count(power_component):
    """Копия компонента с вычисленным количеством лайков."""
    item = dict(power_component)
    item["likes_count"] = len(power_component["likes"])
    return item


def first_published_power_component_id():
    """Идентификатор первого опубликованного компонента — для ссылки на ленту."""
    published = get_published_power_components()
    return published[0]["id"] if published else 0


templates.env.globals["first_published_power_component_id"] = first_published_power_component_id


@router.get("/")
@router.get("/power_components")
def get_power_components_tile(
    request: Request,
    max_power: int | None = Query(default=None, ge=POWER_MIN, le=POWER_MAX),
):
    """Плитка: каталог опубликованных компонентов в две колонки."""
    items = get_published_power_components()

    current_max_power = POWER_MAX if max_power is None else max_power

    items = [c for c in items if c["power_watt"] <= current_max_power]

    tile_power_components = [with_likes_count(c) for c in items]

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


@router.get("/power_components/feed/{power_component_id}")
def get_power_component_feed(
    request: Request,
    power_component_id: int,
    is_next: bool = Query(default=False, alias="next"),
):
    """Лента: карточка компонента с автовоспроизводимым видео."""
    items = get_published_power_components()

    if not items:
        raise HTTPException(status_code=404, detail="Нет опубликованных компонентов")

    if is_next:
        following = [c for c in items if c["id"] > power_component_id]
        power_component = following[0] if following else items[0]
    else:
        power_component = next((c for c in items if c["id"] == power_component_id), None)

    if power_component is None:
        raise HTTPException(status_code=404, detail="Компонент не найден")

    return templates.TemplateResponse(
        request=request,
        name="feed.html",
        context={"power_component": with_likes_count(power_component)},
    )


@router.get("/power_components/draft")
def get_power_component_draft(request: Request):
    """Добавление: отображает единственный компонент в статусе «черновик»."""
    draft = next((c for c in power_components if c["status"] == "черновик"), None)

    return templates.TemplateResponse(
        request=request,
        name="add.html",
        context={"power_component": draft},
    )
