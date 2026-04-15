# План реализации: Система контроля заданий на выпуск продукции

## Контекст
Веб-приложение для управления сменными заданиями на производстве с асинхронной обработкой задач, файловым хранилищем и внешними интеграциями.

**ТЗ:** `C:\Users\Андрей\Desktop\Тестовое для клода.html` (Tilda-страница с полным техническим заданием)

---

## Технологический стек
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0+ (async), Pydantic v2
- **БД:** PostgreSQL 16, Alembic (миграции)
- **Async:** RabbitMQ (broker), Celery 5.3+ (tasks), Redis (result backend), Celery Beat (scheduler)
- **Кэш:** Redis 7+
- **Файлы:** MinIO (S3-compatible)
- **Контейнеры:** Docker, Docker Compose (8 сервисов)

---

## Архитектура (слоистая)

```
API (routers) → Services → Repositories → Models (SQLAlchemy)
                  ↓              ↓
              Cache (Redis)   Database (PostgreSQL)
                  ↓
            Celery Tasks → MinIO / Webhooks
```

---

## Модели данных (5 штук)
1. **WorkCenter** — рабочий центр (identifier, name)
2. **Batch** — сменное задание/партия (batch_number+batch_date уникальный, FK→WorkCenter)
3. **Product** — единица продукции (unique_code, FK→Batch, is_aggregated)
4. **WebhookSubscription** — подписка на события (url, events[], secret_key)
5. **WebhookDelivery** — доставка webhook (status, attempts, payload)

---

## API Endpoints

### Базовые CRUD (6)
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | /api/v1/batches | Создание партий (массив, русские поля с alias) |
| GET | /api/v1/batches/{id} | Получение партии с продуктами |
| PATCH | /api/v1/batches/{id} | Обновление (is_closed→closed_at автоматически) |
| GET | /api/v1/batches | Список с фильтрацией и пагинацией |
| POST | /api/v1/products | Добавление продукции |
| POST | /api/v1/batches/{id}/aggregate | Синхронная аггрегация |

### Асинхронные (через Celery, возвращают 202 + task_id)
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | /api/v1/batches/{id}/aggregate-async | Массовая аггрегация (>100 единиц) |
| POST | /api/v1/batches/{id}/reports | Генерация Excel/PDF отчёта |
| POST | /api/v1/batches/import | Импорт из Excel/CSV (multipart) |
| POST | /api/v1/batches/export | Экспорт в Excel/CSV |
| GET | /api/v1/tasks/{task_id} | Статус Celery задачи |

### Webhooks
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | /api/v1/webhooks | Создание подписки |
| GET | /api/v1/webhooks | Список подписок |
| PATCH | /api/v1/webhooks/{id} | Обновление подписки |
| DELETE | /api/v1/webhooks/{id} | Удаление подписки |
| GET | /api/v1/webhooks/{id}/deliveries | История доставок |

### Аналитика
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | /api/v1/analytics/dashboard | Общая статистика (из кэша) |
| GET | /api/v1/batches/{id}/statistics | Статистика по партии |
| POST | /api/v1/analytics/compare-batches | Сравнение партий |

---

## Celery Beat (периодические задачи)
- `auto_close_expired_batches` — ежедневно в 01:00
- `cleanup_old_files` — ежедневно в 02:00
- `update_cached_statistics` — каждые 5 мин
- `retry_failed_webhooks` — каждые 15 мин

---

## Webhook события (6 типов)
batch_created, batch_updated, batch_closed, product_aggregated, report_generated, import_completed

---

## Кэширование (Redis TTL)
- Dashboard stats: 300s (5 мин)
- Batch list: 60s (1 мин)
- Batch detail: 600s (10 мин)
- Batch statistics: 300s (5 мин)
- Инвалидация при CRUD операциях

---

## Docker Compose — 8 сервисов
api (FastAPI), postgres, redis, rabbitmq, celery_worker, celery_beat, flower, minio

---

## Статус реализации

### Выполнено (коммит fb67646)
- [x] Core: database, cache, exceptions, dependencies
- [x] Models: все 5 моделей с индексами и связями
- [x] Repositories: base + 3 специфичных
- [x] Schemas: все Pydantic v2 схемы
- [x] Services: batch, product, webhook, analytics
- [x] Celery: app + 6 файлов задач + Beat schedule
- [x] Utils: HMAC, Excel gen/parse, PDF gen
- [x] Storage: MinIO service + init script
- [x] API: 5 роутеров со всеми эндпоинтами
- [x] Docker: Dockerfile + docker-compose.yml (8 сервисов)
- [x] Alembic: env.py + alembic.ini
- [x] Tests: conftest.py с async fixtures

### Нужно доделать
- [ ] Alembic: сгенерировать первую миграцию (`alembic revision --autogenerate`)
- [ ] Тесты: unit и integration тесты
- [ ] Запуск и проверка через docker-compose
- [ ] Rate limiting middleware
- [ ] README.md (если нужно)

---

## Верификация
1. `docker-compose up -d`
2. `alembic upgrade head`
3. Swagger UI: http://localhost:8000/docs
4. Тестовые запросы ко всем эндпоинтам
5. `pytest`
