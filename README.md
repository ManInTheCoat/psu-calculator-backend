# PC Power Calc - бэкенд

Тема 18: определение необходимой мощности блока питания для ПК.
Услуга - компонент ПК (`power_component`) с потребляемой мощностью и весом.

Стек: FastAPI, SQLAlchemy 2.0 (async, asyncpg), Alembic, PostgreSQL, MinIO, Redis, Pydantic.

## Лабораторная 4 - авторизация

Авторизация через сессии и куки. Сессии хранятся в Redis (`core/sessions.py`), текущий пользователь определяется по куке `session_id` (`core/current_user.py`).

1. `POST /api/users/login` проверяет логин и пароль, создаёт в Redis ключ `session:<uuid>` со значением `{"user_id": 1, "login": "builder"}` и сроком жизни сутки (`SESSION_TTL_SECONDS`) и отвечает заголовком `Set-Cookie: session_id=<uuid>; HttpOnly; SameSite=Lax`.
2. Браузер (или Postman - заголовком `Cookie`) отправляет куку с каждым запросом. Сервер ищет сессию в Redis и получает пользователя.
3. `POST /api/users/logout` удаляет ключ из Redis и куку. По истечении срока Redis удаляет ключ сам.

Две зависимости FastAPI:

- `get_current_user_optional` - гость или пользователь: для методов чтения, гостю возвращается `None`;
- `get_current_user` - только авторизованный пользователь: для методов создателя, без действующей сессии ответ `401`. Кука описана схемой `APIKeyCookie`, поэтому в Swagger у этих методов замочек.

| № | Метод | Гость | Создатель (после входа) |
|---|---|---|---|
| 1 | GET список | 200, `is_mine` = 0 | 200, `is_mine` для текущего пользователя |
| 2 | GET лента | 200, `is_liked` и `is_mine` = 0 | 200, признаки для текущего пользователя |
| 3 | GET черновик | 401 | 200, свой черновик |
| 4 | POST добавление | 401 | 201, создатель берется из сессии |
| 5 | PUT публикация | 401 | 200, свой черновик (чужой 403) |
| 6 | DELETE удаление | 401 | 200, свой компонент (чужой 403) |
| 7 | POST лайк | 401 | 200 |
| 8 | POST регистрация | 201 | 201 |
| 9 | POST вход | 200 | 200 |
| 10 | POST выход | 401 | 204 |

### Просмотр сессий в Redis

```bash
docker exec -it pc_power_redis redis-cli KEYS "*"
docker exec -it pc_power_redis redis-cli GET session:<uuid>
docker exec -it pc_power_redis redis-cli TTL session:<uuid>
```

`KEYS` - список сессий, `GET` - пользователь сессии, `TTL` - сколько секунд сессии осталось жить.

### Логины активных сессий (Lua-скрипт)

Скрипт `scripts/active_sessions.lua` перебирает ключи `session:*`, достает из каждой сессии логин и возвращает строки `логин TTL`, где TTL - сколько секунд сессии осталось жить.

```bash
docker cp scripts/active_sessions.lua pc_power_redis:/data/active_sessions.lua
docker exec -it pc_power_redis redis-cli --eval /data/active_sessions.lua
```

Тот же скрипт одной строкой через `EVAL`:

```bash
docker exec -it pc_power_redis redis-cli EVAL "local r = {} for _, k in ipairs(redis.call('KEYS', ARGV[1])) do local v = redis.call('GET', k) if v then table.insert(r, cjson.decode(v)['login'] .. ' ' .. redis.call('TTL', k)) end end return r" 0 "session:*"
```

### Проверка в Postman (ЛР4)

Импортировать `postman/psu_calculator_lab4.postman_collection.json`. Переменные в коллекции не используются: адрес `http://127.0.0.1:8000/...` и заголовок `Cookie: session_id=<значение>` записаны в каждом запросе явно.

1. Войти через Swagger (`POST /api/users/login`) в режиме инкогнито.
2. В браузере F12, Application, Cookies, `http://127.0.0.1:8000` скопировать значение `session_id`.
3. Вставить его в заголовок `Cookie` запросов 01-07 (вкладка Headers, галочка у заголовка стоит).
4. В запросах 04-07 указать id своего черновика (его возвращает запрос 02), в запросе 10 - куку из ответа запроса 09.

Если снять галочку у заголовка `Cookie`, запрос уходит от гостя: список и лента работают, методы создателя отвечают `401`. Хранилище кук Postman у запросов отключено (Settings, Disable cookie jar), поэтому пользователь определяется только этим заголовком.

## Лабораторная 3 - веб-сервис

10 методов: 7 в домене компонентов ПК (услуги) и 3 в домене пользователей. Все адреса начинаются с `/api`.

Ответ - сами данные (объект или массив) без обёрток. Результат запроса передаётся HTTP-кодом: `200` - успех, `201` - создано, `204` - успех без тела, `400` - некорректный запрос (неверный тип, значение вне диапазона, передано системное поле), `401` - требуется авторизация (ЛР4), `403` - чужой компонент, `404` - не найдено или удалено, `405` - HTTP-метод не поддерживается, `409` - конфликт с текущим состоянием (второй черновик, повторная публикация, занятый логин), `500` - ошибка сервера. При ошибке тело стандартное для FastAPI: `{"detail": "описание ошибки"}`.

Системные поля (`id`, `status`, `creator_id`, `created_at`, `formed_at`) с клиента передавать нельзя: входные схемы запрещают лишние поля (`extra="forbid"`), такой запрос получает `400`.

### Домен компонентов - `/api/power_components`

| № | Метод | URL | Описание | Входные данные | Выходные данные |
|---|---|---|---|---|---|
| 1 | GET | `/api/power_components?max_power=300` | Список опубликованных компонентов с фильтром по мощности | query: `max_power` int 0-500, необязательный | массив: `id` int, `title` str, `image_url` str, `power_watt` int, `weight_gram` int, `likes_count` int, `is_mine` 0/1 |
| 2 | GET | `/api/power_components/feed?power_component_id=2&next=true` | Лента. Без параметров - первый опубликованный (для панели вкладок); с `power_component_id` - этот компонент; с `power_component_id` и `next=true` - следующий опубликованный после него (после последнего - снова первый) | query: `power_component_id` int ≥ 1, необязательный; `next` bool, необязательный | `id`, `title`, `description`, `image_url`, `video_url`, `power_watt`, `weight_gram`, `formed_at` datetime, `creator` {`id`, `login`}, `likes_count`, `is_liked` 0/1, `is_mine` 0/1 |
| 3 | GET | `/api/power_components/draft` | Черновик текущего пользователя (не более одного), ид не указывается | - | `id`, `title`, `description`, `status`, `image_url`, `video_url`, `power_watt`, `weight_gram`, `created_at`, `formed_at`, `creator_id` |
| 4 | POST | `/api/power_components` | Добавление черновика с фото и видео | multipart/form-data: `title` str ≤ 100, `image` файл PNG/JPEG/GIF/WEBP ≤ 5 МБ, `video` файл MP4/MOV/WEBM ≤ 50 МБ | как в п. 3, код `201` |
| 5 | PUT | `/api/power_components/{id}/publish` | Публикация: `draft` → `published`, `formed_at = now()` | JSON: `description` str ≤ 500, `power_watt` int 1-500, `weight_gram` int 1-100000 | как в п. 3 |
| 6 | DELETE | `/api/power_components/{id}` | Логическое удаление своего компонента: статус `deleted` | path: `id` | `id`, `status` |
| 7 | POST | `/api/power_components/{id}/like` | Лайк от текущего пользователя | JSON: `like` 0/1 (1 - поставить, 0 - отменить) | `power_component_id`, `is_liked`, `likes_count` |

Признаки 0/1 вычисляются на бэкенде для текущего пользователя и нужны фронтенду:

- `is_mine` в списке - компонент создан текущим пользователем. Плитка по нему показывает кнопку «Удалить» только у своих карточек: удалить можно только своё.
- `is_liked` в ленте - текущий пользователь уже поставил лайк. Лента по нему закрашивает сердце и решает, что отправить в лайк: при `is_liked = 0` - `like = 1`, при `is_liked = 1` - `like = 0`.
- `is_mine` в ленте - тот же признак своего компонента, чтобы и в ленте показать удаление только у своей карточки.

Правила смены статуса: создать можно только черновик и только если у пользователя нет другого черновика; опубликовать - только свой черновик; вернуть в черновик нельзя; удалённые записи (`deleted`) на клиент не передаются.

Файлы проверяются по сигнатуре (первым байтам), а не по расширению. В MinIO (бакет `power-components`) они сохраняются под латинскими именами `power_component_<id>_image_<8 символов>.png` и `power_component_<id>_video_<8 символов>.mp4`, публичные ссылки записываются в `image_url` и `video_url`.

### Домен пользователей - `/api/users`

| № | Метод | URL | Описание | Входные данные | Выходные данные |
|---|---|---|---|---|---|
| 8 | POST | `/api/users/register` | Регистрация | JSON: `login` str 3-50 (латиница, цифры, `_ . -`), `password` str 6-128 | `id`, `login`, код `201` |
| 9 | POST | `/api/users/login` | Аутентификация: сессия в Redis и кука `session_id` (ЛР4) | JSON: `login`, `password` | `id`, `login`; заголовок `Set-Cookie`; неверные данные - `401` |
| 10 | POST | `/api/users/logout` | Деавторизация: удаление сессии из Redis и куки (ЛР4) | кука `session_id` | без тела, код `204`; без куки - `401` |

Пароль хранится как хеш PBKDF2-SHA256 (`core/security.py`) и никогда не возвращается в ответах.

### Таблицы БД

**`users`** - пользователи

| Поле | Тип | Описание |
|---|---|---|
| `id` | INTEGER, PK | Идентификатор |
| `login` | VARCHAR(50), UNIQUE, NOT NULL | Логин |
| `password` | VARCHAR(255), NOT NULL | Хеш пароля |

**`power_components`** - компоненты ПК (услуги)

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

Не более одного черновика на пользователя - частичный уникальный индекс `uq_one_draft_per_creator` (`creator_id`, условие `status = 'draft'`).

**`power_component_likes`** - лайки, связь м-м пользователей и компонентов

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
| `core/current_user.py` | Текущий пользователь по куке `session_id` (ЛР4) |
| `core/sessions.py` | Сессии в Redis: создание, чтение, удаление (ЛР4) |
| `core/config.py` | Настройки из `.env` |
| `scripts/active_sessions.lua` | Lua-скрипт Redis: логины активных сессий (ЛР4) |
| `postman/psu_calculator_lab4.postman_collection.json` | Коллекция запросов Postman ЛР4 (без переменных, кука в заголовке) |
| `postman/psu_calculator_lab3.postman_collection.json` | Коллекция запросов Postman ЛР3 |

### Проверка в Postman (ЛР3)

Импортировать `postman/psu_calculator_lab3.postman_collection.json` (File → Import). В коллекции 10 запросов - по одному на каждый метод, выполнять по порядку 01-10: запрос 02 сохраняет id созданного черновика в переменную `componentId`, остальные его используют. Запрос 05 - единственный метод ленты: со снятыми галочками у параметров это лента без ид, с включёнными `power_component_id` и `next=true` - следующий после указанного компонента. В каждом запросе есть автотесты кода ответа; всю коллекцию можно прогнать через Run collection.

После импорта Postman не читает файлы по путям из коллекции: в запросе 02 нужно один раз выбрать фото и видео заново (значение поля `image` / `video` → Select Files) и сохранить запрос (Ctrl+S). Без файлов черновик создаётся с пустыми `image_url` и `video_url` - тесты «Фото в MinIO» и «Видео в MinIO» в запросе 02 это покажут.

Swagger: `http://127.0.0.1:8000/docs`.

## Лабораторная 2 - HTML-страницы

Страницы на шаблонах Jinja2: `/power_components` (плитка с фильтром), `/power_components/feed/{id}` (лента), `/power_components/draft` (добавление). Логическое удаление на странице плитки выполняется сырым SQL (`UPDATE ... SET status = 'deleted'`). Если у фото или видео пустой `url`, показываются заглушки из `static/img/default-component.png` и `static/video/default-component.mp4`.

## Запуск

```bash
docker compose up -d
pip install -r requirements.txt
alembic upgrade head
python main.py
```

Переменные окружения - в `.env` (пример в `env.example`). Настройки MinIO (`MINIO_*`) и Redis (`REDIS_*`, `SESSION_*`) необязательны: по умолчанию используются сервисы из `docker-compose.yml`.

- Adminer: `http://localhost:8081` (система PostgreSQL, сервер `postgres`, пользователь `pc_builder`, пароль `pc_builder_pass`, БД `pc_power_db`)
- Консоль MinIO: `http://localhost:9001` (`root` / `rootpassword`)
- Redis: `localhost:6379`, консоль - `docker exec -it pc_power_redis redis-cli`
