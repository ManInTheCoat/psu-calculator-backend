# PC Power Calc — бэкенд

Тема 18: определение необходимой мощности блока питания для ПК.
Услуга — компонент ПК (`power_component`) с потребляемой мощностью и весом.

Стек: FastAPI, SQLAlchemy 2.0 (async, asyncpg), Alembic, PostgreSQL, MinIO, Pydantic.

## Лабораторная 3 — веб-сервис

10 методов: 7 в домене компонентов ПК (услуги) и 3 в домене пользователей. Все адреса начинаются с `/api`.

Ответ — сами данные (объект или массив) без обёрток. Результат запроса передаётся HTTP-кодом: `200` — успех, `201` — создано, `204` — успех без тела, `400` — некорректный запрос (неверный тип, значение вне диапазона, передано системное поле), `403` — чужой компонент, `404` — не найдено или удалено, `405` — HTTP-метод не поддерживается, `409` — конфликт с текущим состоянием (второй черновик, повторная публикация, занятый логин), `500` — ошибка сервера. При ошибке тело стандартное для FastAPI: `{"detail": "описание ошибки"}`.

Пользователь-создатель до авторизации (ЛР4) зафиксирован константой `CREATOR_ID = 1` в функции-singleton `get_current_user()` (`core/current_user.py`). Все методы получают его через `Depends(get_current_user)`.

Системные поля (`id`, `status`, `creator_id`, `created_at`, `formed_at`) с клиента передавать нельзя: входные схемы запрещают лишние поля (`extra="forbid"`), такой запрос получает `400`.

### Домен компонентов — `/api/power_components`

| № | Метод | URL | Описание | Входные данные | Выходные данные |
|---|---|---|---|---|---|
| 1 | GET | `/api/power_components?max_power=300` | Список опубликованных компонентов с фильтром по мощности | query: `max_power` int 0–500, необязательный | массив: `id` int, `title` str, `image_url` str, `power_watt` int, `weight_gram` int, `likes_count` int, `is_mine` 0/1 |
| 2 | GET | `/api/power_components/feed?power_component_id=2&next=true` | Лента. Без параметров — первый опубликованный (для панели вкладок); с `power_component_id` — этот компонент; с `power_component_id` и `next=true` — следующий опубликованный после него (после последнего — снова первый) | query: `power_component_id` int ≥ 1, необязательный; `next` bool, необязательный | `id`, `title`, `description`, `image_url`, `video_url`, `power_watt`, `weight_gram`, `formed_at` datetime, `creator` {`id`, `login`}, `likes_count`, `is_liked` 0/1, `is_mine` 0/1 |
| 3 | GET | `/api/power_components/draft` | Черновик текущего пользователя (не более одного), ид не указывается | — | `id`, `title`, `description`, `status`, `image_url`, `video_url`, `power_watt`, `weight_gram`, `created_at`, `formed_at`, `creator_id` |
| 4 | POST | `/api/power_components` | Добавление черновика с фото и видео | multipart/form-data: `title` str ≤ 100, `image` файл PNG/JPEG/GIF/WEBP ≤ 5 МБ, `video` файл MP4/MOV/WEBM ≤ 50 МБ | как в п. 3, код `201` |
| 5 | PUT | `/api/power_components/{id}/publish` | Публикация: `draft` → `published`, `formed_at = now()` | JSON: `description` str ≤ 500, `power_watt` int 1–500, `weight_gram` int 1–100000 | как в п. 3 |
| 6 | DELETE | `/api/power_components/{id}` | Логическое удаление своего компонента: статус `deleted` | path: `id` | `id`, `status` |
| 7 | POST | `/api/power_components/{id}/like` | Лайк от текущего пользователя | JSON: `like` 0/1 (1 — поставить, 0 — отменить) | `power_component_id`, `is_liked`, `likes_count` |

Признаки 0/1 вычисляются на бэкенде для текущего пользователя и нужны фронтенду:

- `is_mine` в списке — компонент создан текущим пользователем. Плитка по нему показывает кнопку «Удалить» только у своих карточек: удалить можно только своё.
- `is_liked` в ленте — текущий пользователь уже поставил лайк. Лента по нему закрашивает сердце и решает, что отправить в лайк: при `is_liked = 0` — `like = 1`, при `is_liked = 1` — `like = 0`.
- `is_mine` в ленте — тот же признак своего компонента, чтобы и в ленте показать удаление только у своей карточки.

Правила смены статуса: создать можно только черновик и только если у пользователя нет другого черновика; опубликовать — только свой черновик; вернуть в черновик нельзя; удалённые записи (`deleted`) на клиент не передаются.

Файлы проверяются по сигнатуре (первым байтам), а не по расширению. В MinIO (бакет `power-components`) они сохраняются под латинскими именами `power_component_<id>_image_<8 символов>.png` и `power_component_<id>_video_<8 символов>.mp4`, публичные ссылки записываются в `image_url` и `video_url`.

### Домен пользователей — `/api/users`

| № | Метод | URL | Описание | Входные данные | Выходные данные |
|---|---|---|---|---|---|
| 8 | POST | `/api/users/register` | Регистрация | JSON: `login` str 3–50 (латиница, цифры, `_ . -`), `password` str 6–128 | `id`, `login`, код `201` |
| 9 | POST | `/api/users/login` | Аутентификация — заглушка до ЛР4 | JSON: `login`, `password` | `id`, `login` текущего пользователя |
| 10 | POST | `/api/users/logout` | Деавторизация — заглушка до ЛР4 | — | без тела, код `204` |

Пароль хранится как хеш PBKDF2-SHA256 (`core/security.py`) и никогда не возвращается в ответах.

### Таблицы БД

**`users`** — пользователи

| Поле | Тип | Описание |
|---|---|---|
| `id` | INTEGER, PK | Идентификатор |
| `login` | VARCHAR(50), UNIQUE, NOT NULL | Логин |
| `password` | VARCHAR(255), NOT NULL | Хеш пароля |

**`power_components`** — компоненты ПК (услуги)

| Поле | Тип | Описание |
|---|---|---|
| `id` | INTEGER, PK | Идентификатор |
| `title` | VARCHAR(100), NOT NULL | Название |
| `description` | VARCHAR(500) | Краткое описание |
| `status` | VARCHAR(20), NOT NULL | `draft` / `published` / `deleted` |
| `image_url` | VARCHAR(255), NOT NULL, по умолчанию `''` | Ссылка на фото в MinIO |
| `video_url` | VARCHAR(255), NOT NULL, по умолчанию `''` | Ссылка на видео в MinIO |
| `power_watt` | INTEGER | Потребляемая мощность, Вт |
| `weight_gram` | INTEGER | Вес, г |
| `created_at` | TIMESTAMP, NOT NULL, `now()` | Дата создания |
| `formed_at` | TIMESTAMP | Дата формирования (публикации) |
| `creator_id` | INTEGER, FK → `users.id`, NOT NULL | Создатель |

Не более одного черновика на пользователя — частичный уникальный индекс `uq_one_draft_per_creator` (`creator_id`, условие `status = 'draft'`).

**`power_component_likes`** — лайки, связь м-м пользователей и компонентов

| Поле | Тип | Описание |
|---|---|---|
| `id` | INTEGER, PK | Идентификатор |
| `user_id` | INTEGER, FK → `users.id`, NOT NULL | Кто поставил лайк |
| `power_component_id` | INTEGER, FK → `power_components.id`, NOT NULL | Какому компоненту |

Пара (`user_id`, `power_component_id`) уникальна. Каскадное удаление не используется (внешние ключи `RESTRICT`).

### Структура проекта

| Папка / файл | Назначение |
|---|---|
| `api/power_components_api.py` | Методы домена компонентов |
| `api/users_api.py` | Методы домена пользователей |
| `api/errors.py` | Ошибки `/api`: код 400 для ошибок валидации, тело `{"detail": ...}` |
| `api/handlers.py` | HTML-страницы ЛР2 (шаблоны Jinja2) |
| `schemas/` | Сериализаторы Pydantic: ответы и входные данные |
| `models/` | Модели SQLAlchemy (таблицы БД) |
| `services/minio_storage.py` | Проверка и загрузка файлов в MinIO |
| `core/current_user.py` | Singleton текущего пользователя |
| `core/config.py` | Настройки из `.env` |
| `postman/psu_calculator_lab3.postman_collection.json` | Коллекция запросов Postman |

### Проверка в Postman

Импортировать `postman/psu_calculator_lab3.postman_collection.json` (File → Import). В коллекции 10 запросов — по одному на каждый метод, выполнять по порядку 01–10: запрос 02 сохраняет id созданного черновика в переменную `componentId`, остальные его используют. Запрос 05 — единственный метод ленты: со снятыми галочками у параметров это лента без ид, с включёнными `power_component_id` и `next=true` — следующий после указанного компонента. В каждом запросе есть автотесты кода ответа; всю коллекцию можно прогнать через Run collection.

После импорта Postman не читает файлы по путям из коллекции: в запросе 02 нужно один раз выбрать фото и видео заново (значение поля `image` / `video` → Select Files) и сохранить запрос (Ctrl+S). Без файлов черновик создаётся с пустыми `image_url` и `video_url` — тесты «Фото в MinIO» и «Видео в MinIO» в запросе 02 это покажут.

Swagger: `http://127.0.0.1:8000/docs`.

## Лабораторная 2 — HTML-страницы

Страницы на шаблонах Jinja2: `/power_components` (плитка с фильтром), `/power_components/feed/{id}` (лента), `/power_components/draft` (добавление). Логическое удаление на странице плитки выполняется сырым SQL (`UPDATE ... SET status = 'deleted'`). Если у фото или видео пустой `url`, показываются заглушки из `static/img/default-component.png` и `static/video/default-component.mp4`.

## Запуск

```bash
docker compose up -d
pip install -r requirements.txt
alembic upgrade head
python main.py
```

Переменные окружения — в `.env` (пример в `env.example`). Настройки MinIO (`MINIO_*`) необязательны: по умолчанию используется MinIO из `docker-compose.yml`.

- Adminer: `http://localhost:8081` (система PostgreSQL, сервер `postgres`, пользователь `pc_builder`, пароль `pc_builder_pass`, БД `pc_power_db`)
- Консоль MinIO: `http://localhost:9001` (`root` / `rootpassword`)
