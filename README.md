# Лабораторная 2 — база данных и ORM

БД: PostgreSQL, ORM: SQLAlchemy 2.0 (async), миграции: Alembic. Три таблицы:

| Таблица | Описание |
|---|---|
| `users` | Пользователи (`id`, `login`) |
| `power_components` | Компоненты: `title`, `description`, `status` (`draft`/`published`/`deleted`), `image_url`, `video_url`, `power_watt`, `weight_gram`, `created_at`, `formed_at`, `creator_id` (FK → `users`) |
| `power_component_likes` | Лайки, м-м: `user_id` (FK → `users`), `power_component_id` (FK → `power_components`) |

У пользователя может быть не более одного черновика — ограничение задано частичным уникальным индексом в БД (`status = 'draft'`).
Каскадное удаление не используется: внешние ключи со стандартным поведением `RESTRICT`.

Шесть HTTP-методов:

| Метод | Адрес | Реализация |
|---|---|---|
| GET | `/power_components?max_power=...` | ORM |
| GET | `/power_components/feed` | ORM |
| GET | `/power_components/feed/{id}?next=true` | ORM |
| GET | `/power_components/draft` | ORM |
| POST | `/power_components/draft` | ORM |
| POST | `/power_components/{id}/publish` | ORM |
| POST | `/power_components/{id}/delete` | сырой SQL (`UPDATE ... SET status = 'deleted'`) |

Если у изображения/видео пустой `url` или файл недоступен по ссылке, в интерфейсе подставляются заглушки из `static/img/default-component.png` и `static/video/default-component.mp4`.

### Запуск

```bash
docker compose up -d
alembic upgrade head
python main.py
```

Переменные окружения — в `.env` (см. `.env.example` при наличии), подключение к БД настраивается через `core/config.py`.

Adminer: `http://localhost:8081` (система PostgreSQL, сервер `postgres`, пользователь `pc_builder`, пароль `pc_builder_pass`, БД `pc_power_db`).
