# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🏗️ Архитектура системы

**Production Control System** — система управления производственными заданиями с поддержкой асинхронных операций, кэширования и вебхуков.

### Слои приложения

```
src/
├── main.py              # FastAPI приложение, настройка middleware и роутеры
├── core/                # Инфраструктура
│   ├── config.py       # Конфигурация (Pydantic Settings из .env)
│   ├── database.py     # SQLAlchemy (async, PostgreSQL)
│   ├── cache.py        # Redis кэширование (RedisCache)
│   ├── dependencies.py # FastAPI зависимости (get_db, get_cache)
│   └── exceptions.py   # Кастомные исключения
├── domain/             # Бизнес-логика (слой доменов)
│   ├── models/        # SQLAlchemy ORM модели (Batch, Product, WorkCenter, Webhook)
│   ├── services/      # Бизнес-логика (BatchService, ProductService и т.д.)
│   └── repositories/  # Репозитории для доступа к БД (паттерн Repository)
├── api/v1/            # Слой API
│   ├── routers/       # Эндпоинты (batches, products, tasks, webhooks, analytics)
│   └── schemas/       # Pydantic DTO схемы для валидации
├── storage/           # Работа с S3-like хранилищем (MinIO)
│   └── minio_service.py
├── tasks/             # Celery задачи
│   ├── aggregation.py # Агрегация данных
│   ├── reports.py     # Генерация отчётов (Excel, PDF)
│   ├── imports.py     # Импорт данных
│   ├── exports.py     # Экспорт данных
│   ├── webhooks.py    # Отправка вебхуков
│   └── scheduled.py   # Плановые задачи (Beat)
├── utils/             # Утилиты
│   ├── hmac_utils.py   # Подпись вебхуков
│   ├── excel_generator.py # Excel
│   ├── pdf_generator.py   # PDF (ReportLab)
│   └── excel_parser.py    # Парсинг Excel
└── celery_app.py      # Конфигурация Celery и Beat
```

### Инфраструктура

- **API**: FastAPI (async)
- **БД**: PostgreSQL + asyncpg (async драйвер)
- **Кэш**: Redis (RedisCache с TTL)
- **Очередь**: RabbitMQ (AMQP) + Celery
- **Scheduler**: Celery Beat (плановые задачи)
- **Хранилище**: MinIO (S3-compatible)
- **Документы**: Excel (openpyxl), PDF (ReportLab)

### Ключевые паттерны

1. **Repository паттерн** — все запросы к БД через репозитории
2. **Service слой** — бизнес-логика отделена от API
3. **Async/await** — весь код async
4. **Dependency Injection** — FastAPI зависимости (get_db, get_cache)
5. **Pydantic Schemas** — валидация и сериализация
6. **Celery Tasks** — асинхронные операции + плановые задачи
7. **Redis TTL кэширование** — кэш со сроком действия для список/деталей

---

## 🚀 Запуск проекта

### Docker Compose (рекомендуется)

```bash
# Запустить все сервисы (API, БД, Redis, RabbitMQ, MinIO, Celery)
docker-compose up -d

# API на http://localhost:8000
# Flower (мониторинг Celery) на http://localhost:5555
# MinIO на http://localhost:9000 (login: minioadmin/minioadmin)
# RabbitMQ на http://localhost:15672 (login: admin/admin)

# Остановить
docker-compose down
```

### Локальная разработка

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Создать .env файл (см. .env.example)
cp .env.example .env

# 3. Инициализировать БД (Alembic миграции)
alembic upgrade head

# 4. Запустить API (одна сессия)
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 5. Запустить Celery worker (другая сессия)
celery -A src.celery_app worker --loglevel=info

# 6. Запустить Celery Beat (третья сессия, опционально)
celery -A src.celery_app beat --loglevel=info

# 7. Запустить Flower для мониторинга (четвёртая сессия, опционально)
celery -A src.celery_app flower
```

---

## 📋 Часто используемые команды

### Тесты

```bash
# Запустить все тесты
pytest

# Запустить тесты конкретного модуля
pytest tests/test_batches.py

# Запустить с подробным выводом
pytest -v

# Запустить только отмеченные тесты
pytest -m "mark_name"

# Показать покрытие кода
pytest --cov=src
```

### Миграции (Alembic)

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "Описание"

# Применить миграции
alembic upgrade head

# Откатить одну миграцию
alembic downgrade -1

# Посмотреть текущую версию
alembic current
```

### Форматирование и проверка кода

```bash
# Форматирование (если установлен black)
black src tests

# Проверка (если установлены рабочие инструменты)
flake8 src tests
isort src tests --check  # проверка сортировки импортов
```

### Инициализация MinIO

```bash
# Создать бакеты при первом запуске
python scripts/init_minio.py
```

---

## 📐 Структура данных и модели

### Основные сущности

- **Batch** — производственная партия (статусы: pending, in_progress, completed, cancelled)
- **Product** — продукт в батче
- **WorkCenter** — рабочий центр/участок
- **Webhook** — конфигурация вебхука для отправки событий

### Кэширование

Используется Redis с разными TTL в зависимости от данных:
- Dashboard: 300 сек (5 мин)
- Список батчей: 60 сек
- Детали батча: 600 сек (10 мин)
- Статистика: 300 сек

Ключи формируются с префиксом типа сущности (например: `batch:123`, `dashboard:stats`).

---

## 🔍 Важные файлы и точки входа

| Файл | Назначение |
|------|-----------|
| `src/main.py` | Точка входа FastAPI, настройка middleware |
| `src/celery_app.py` | Конфигурация Celery, Beat schedule |
| `src/core/config.py` | Все настройки из .env (Pydantic Settings) |
| `src/core/database.py` | SQLAlchemy engine и sessionmaker |
| `docker-compose.yml` | Описание всех сервисов для разработки |
| `alembic/env.py` | Настройка миграций |
| `tests/conftest.py` | Pytest fixtures для тестирования |

---

## 🛠️ Разработка нового функционала

### Добавить новый эндпоинт

1. Создать Pydantic schema в `src/api/v1/schemas/`
2. Создать метод в Service (например, `src/domain/services/batch_service.py`)
3. Добавить эндпоинт в роутер (например, `src/api/v1/routers/batches.py`)
4. Добавить репозиторий метод если нужен доступ к БД

### Добавить асинхронную задачу

1. Добавить функцию в `src/tasks/` с декоратором `@celery_app.task`
2. Если это плановая задача (Beat), добавить в `celery_app.conf.beat_schedule`
3. Вызвать через `.delay()` из service или API

### Добавить новую таблицу

1. Создать модель в `src/domain/models/`
2. Запустить `alembic revision --autogenerate -m "Описание"`
3. Запустить `alembic upgrade head`
4. Создать репозиторий в `src/domain/repositories/`
5. Создать service в `src/domain/services/`
6. Создать schemas в `src/api/v1/schemas/`
7. Добавить роутер в `src/api/v1/routers/`

---

## ⚙️ Конфигурация и переменные окружения

Все параметры читаются из `.env` файла через `src/core/config.py`. Ключевые переменные:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
DATABASE_SYNC_URL=postgresql://user:pass@host:5432/db  # для Alembic
REDIS_URL=redis://localhost:6379
CELERY_BROKER_URL=amqp://user:pass@localhost:5672//
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
SECRET_KEY=change-me-in-production
DEBUG=true
LOG_LEVEL=INFO
```

---

## 📝 Практические советы

1. **Async/await**: Весь код async. Используй `async def`, `await`, не смешивай sync и async
2. **Зависимости**: FastAPI автоматически вводит `get_db`, `get_cache` через dependency_overrides в тестах
3. **Кэш**: Инвалидируй кэш через `cache.delete()` или `cache.delete_pattern()` при изменении данных
4. **Вебхуки**: Подписаны HMAC-SHA256, проверяются перед обработкой
5. **MinIO**: Убедись что бакеты существуют (`minio_service.ensure_buckets()`) перед записью
6. **Тесты**: Используй фикстуры из `tests/conftest.py` (mock_cache, db_session, client)

---

## 🔗 Связанные ресурсы

- FastAPI docs: http://localhost:8000/docs
- Flower (Celery monitoring): http://localhost:5555
- MinIO console: http://localhost:9001
