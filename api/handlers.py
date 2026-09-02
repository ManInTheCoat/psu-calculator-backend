"""Обработчики запросов приложения.

Три GET-метода:
    GET /                     — плитка (каталог) с фильтрацией по TDP
    GET /component/{id}       — лента, карточка одного компонента
    GET /add                  — страница добавления, отображает черновик
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates

from data.collections import components_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_published():
    """Опубликованные компоненты. Черновики и удалённые не попадают в выборку."""
    return [c for c in components_db if c["status"] == "опубликован"]


def with_likes_count(component):
    """Копия компонента с вычисленным количеством лайков."""
    item = dict(component)
    item["likes_count"] = len(component["likes"])
    return item


def first_published_id():
    """Идентификатор первого опубликованного компонента — для ссылки на ленту."""
    published = get_published()
    return published[0]["id"] if published else 0


templates.env.globals["first_published_id"] = first_published_id


@router.get("/")
def get_tile(request: Request, max_tdp: int | None = Query(default=None)):
    """Плитка: каталог опубликованных компонентов в две колонки."""
    items = get_published()

    if max_tdp is not None:
        items = [c for c in items if c["tdp_watt"] <= max_tdp]

    components = [with_likes_count(c) for c in items]

    return templates.TemplateResponse(
        request=request,
        name="tile.html",
        context={"components": components, "max_tdp": max_tdp},
    )


@router.get("/component/{component_id}")
def get_feed(
    request: Request,
    component_id: int,
    is_next: bool = Query(default=False, alias="next"),
):
    """Лента: карточка компонента с автовоспроизводимым видео."""
    items = get_published()

    if not items:
        raise HTTPException(status_code=404, detail="Нет опубликованных компонентов")

    if is_next:
        following = [c for c in items if c["id"] > component_id]
        component = following[0] if following else items[0]
    else:
        component = next((c for c in items if c["id"] == component_id), None)

    if component is None:
        raise HTTPException(status_code=404, detail="Компонент не найден")

    return templates.TemplateResponse(
        request=request,
        name="feed.html",
        context={"c": with_likes_count(component)},
    )


@router.get("/add")
def get_add(request: Request):
    """Добавление: отображает единственный компонент в статусе «черновик»."""
    draft = next((c for c in components_db if c["status"] == "черновик"), None)

    return templates.TemplateResponse(
        request=request,
        name="add.html",
        context={"c": draft},
    )
