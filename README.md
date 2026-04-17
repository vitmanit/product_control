# Production Control System

Backend-сервис для управления сменными заданиями на производстве: партии, продукция, аггрегация, отчёты, вебхуки и аналитика.

## Стек

- **API:** FastAPI (async), Pydantic v2
- **БД:** PostgreSQL 16 + asyncpg, SQLAlchemy 2.0, Alembic
- **Кэш:** Redis 7
- **Очередь задач:** Celery 5.3 + RabbitMQ (broker) + Redis (backend)
- **Scheduler:** Celery Beat
- **Хранилище:** MinIO (S3-compatible)
- **Rate limiting:** SlowAPI
- **Контейнеризация:** Docker Compose (8 сервисов)

## Быстрый старт

### Через Docker Compose

```bash
docker-compose up -d --build
docker-compose exec api alembic upgrade head
```

Доступно:
- API: http://localhost:8000 — Swagger: http://localhost:8000/docs
- Flower: http://localhost:5555
- RabbitMQ: http://localhost:15672 (`admin`/`admin`)
- MinIO: http://localhost:9001 (`minioadmin`/`minioadmin`)

### Локально

```bash
python -m venv .venv && source .venv/Scripts/activate  # Windows bash
pip install -r requirements.txt
cp .env.example .env                                   # правим DATABASE_URL/REDIS_URL/...
alembic upgrade head
uvicorn src.main:app --reload
# в отдельных терминалах:
celery -A src.celery_app worker --loglevel=info
celery -A src.celery_app beat --loglevel=info
```

## Архитектура

```
src/
├── api/v1/          # роутеры + Pydantic-схемы
├── core/            # config, database, cache, rate_limit, exceptions
├── domain/          # models / repositories / services
├── storage/         # MinIO клиент
├── tasks/           # Celery задачи (aggregation, reports, webhooks, ...)
├── utils/           # HMAC, Excel, PDF
├── celery_app.py    # конфигурация Celery и Beat schedule
└── main.py          # сборка FastAPI, middleware, роутеры
```

Слои: `Router → Service → Repository → Model`. Кэш и Celery подключаются через сервисы.

## Модели

| Модель | Ключ | Описание |
|---|---|---|
| `WorkCenter` | `identifier` (unique) | рабочий центр/линия |
| `Batch` | `(batch_number, batch_date)` unique | сменное задание |
| `Product` | `unique_code` (unique) | единица продукции, `is_aggregated` |
| `WebhookSubscription` | `id` | подписка, `events[]`, `secret_key` |
| `WebhookDelivery` | `id` | попытка доставки с подписью HMAC-SHA256 |

## API — примеры

Создание партии (русские поля через Pydantic `alias`):

```bash
curl -X POST http://localhost:8000/api/v1/batches \
  -H "Content-Type: application/json" \
  -d '[{
    "СтатусЗакрытия": false,
    "ПредставлениеЗаданияНаСмену": "Сменное задание №1",
    "РабочийЦентр": "Линия розлива №1",
    "Смена": "Дневная",
    "Бригада": "Бригада А",
    "НомерПартии": 101,
    "ДатаПартии": "2026-04-17",
    "Номенклатура": "Молоко 2.5% 1л",
    "КодЕКН": "EKN-001",
    "ИдентификаторРЦ": "WC-01",
    "ДатаВремяНачалаСмены": "2026-04-17T08:00:00",
    "ДатаВремяОкончанияСмены": "2026-04-17T20:00:00"
  }]'
```

Аггрегация:

```bash
curl -X POST http://localhost:8000/api/v1/products/batches/1/aggregate \
  -H "Content-Type: application/json" \
  -d '{"unique_codes": ["UC-001", "UC-002"]}'
```

Подписка на вебхук:

```bash
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/hook",
    "events": ["batch_created", "batch_closed"],
    "secret_key": "shared-secret"
  }'
```

Каждый вебхук подписывается заголовком `X-Signature` по HMAC-SHA256 от JSON-пейлоада.

## Кэширование (Redis, TTL)

| Ключ | TTL |
|---|---|
| `dashboard_stats` | 5 мин |
| `batches_list:*` | 1 мин |
| `batch_detail:{id}` | 10 мин |
| `batch_statistics:{id}` | 5 мин |

Инвалидация происходит в сервисах на CRUD-операциях.

## Celery Beat (периодические задачи)

- `auto_close_expired_batches` — ежедневно в 01:00
- `cleanup_old_files` — ежедневно в 02:00
- `update_cached_statistics` — каждые 5 мин
- `retry_failed_webhooks` — каждые 15 мин

## Rate limiting

По умолчанию: `RATE_LIMIT_REQUESTS=100` запросов за `RATE_LIMIT_PERIOD=60` секунд на IP. Отключается через `RATE_LIMIT_ENABLED=false`. В продакшне рекомендуется `RATE_LIMIT_STORAGE_URI=redis://...` для распределённого учёта.

## Тесты

```bash
# Только unit (без БД)
pytest tests/unit -v

# Все тесты (нужна БД production_control_test)
createdb -U postgres production_control_test
pytest -v

# Или в docker:
docker-compose exec postgres psql -U postgres -c "CREATE DATABASE production_control_test;"
docker-compose exec api pytest -v
```

URL тестовой БД настраивается через `TEST_DATABASE_URL` (по умолчанию `postgresql+asyncpg://postgres:postgres@localhost:5432/production_control_test`).

## Миграции

```bash
alembic revision --autogenerate -m "описание"
alembic upgrade head
alembic downgrade -1
```

## Переменные окружения

См. `.env.example` — в нём все ключи с дефолтами и комментариями. Для Docker-окружения используется `.env.docker` (хосты указывают на имена сервисов Compose).

## Разработка

- `CLAUDE.md` — инструкция для Claude Code по работе с проектом
- `PLAN.md` — исходный план реализации
