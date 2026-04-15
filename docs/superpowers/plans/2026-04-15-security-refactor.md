# Quick Security Fix Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move all hardcoded credentials to `.env` files, eliminate code duplication in database initialization, and establish production-ready configuration management.

**Architecture:** Single source of truth for configuration (Pydantic Settings in `config.py`), credentials in `.env` files (git-ignored), clear separation between database initialization (`database.py`) and FastAPI dependency injection (`dependencies.py`).

**Tech Stack:** Pydantic Settings, SQLAlchemy, Alembic, FastAPI, Docker Compose

---

## File Structure Overview

**Files to Create:**
- `.env.docker` — Docker Compose credentials
- `.env.example` — Template for all environment variables

**Files to Modify:**
- `docker-compose.yml` — Add `env_file` directive
- `alembic/env.py` — Read database URL from config instead of alembic.ini
- `alembic.ini` — Remove hardcoded `sqlalchemy.url`
- `src/core/database.py` — Remove duplicate `get_db()` if present
- `src/core/dependencies.py` — Ensure single `get_db()` function
- `.gitignore` — Verify `.env*` patterns are ignored

---

## Task 1: Audit Current Code Structure

**Files:**
- Read: `src/core/database.py`
- Read: `src/core/dependencies.py`
- Read: `.gitignore`

**Why:** Understand what we're refactoring before making changes.

- [ ] **Step 1: Read database.py to find current implementation**

```bash
cat src/core/database.py
```

Expected output: You'll see imports, engine/sessionmaker creation, and possibly a `get_db()` function. Note the exact location and content.

- [ ] **Step 2: Read dependencies.py to find FastAPI dependencies**

```bash
cat src/core/dependencies.py
```

Expected output: You'll see the FastAPI `get_db()` dependency. Note if there's duplication with database.py.

- [ ] **Step 3: Read .gitignore to verify env files are ignored**

```bash
cat .gitignore
```

Expected output: Check if `.env` or `.env*` is already listed. If not, we'll add it in Task 8.

- [ ] **Step 4: Note findings for next tasks**

Document:
- Is `get_db()` defined in both files? 
- What exact line numbers?
- Is `.env*` already in .gitignore?

---

## Task 2: Create .env.docker File

**Files:**
- Create: `.env.docker`

This file contains credentials for Docker Compose. It will NOT be committed (git-ignored).

- [ ] **Step 1: Create .env.docker with Docker service credentials**

```bash
cat > .env.docker << 'EOF'
# ============================================
# Application
# ============================================
APP_NAME=Production Control System
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO

# ============================================
# Database
# ============================================
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/production_control
DATABASE_SYNC_URL=postgresql://postgres:postgres@postgres:5432/production_control

# ============================================
# Redis
# ============================================
REDIS_URL=redis://redis:6379
REDIS_CACHE_DB=0
REDIS_CELERY_BACKEND_DB=1

# ============================================
# RabbitMQ / Celery Broker
# ============================================
CELERY_BROKER_URL=amqp://admin:admin@rabbitmq:5672//

# ============================================
# MinIO (S3-compatible Storage)
# ============================================
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_BUCKET_REPORTS=reports
MINIO_BUCKET_EXPORTS=exports
MINIO_BUCKET_IMPORTS=imports

# ============================================
# Security
# ============================================
SECRET_KEY=docker-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ============================================
# Caching TTL (seconds)
# ============================================
CACHE_TTL_DASHBOARD=300
CACHE_TTL_BATCH_LIST=60
CACHE_TTL_BATCH_DETAIL=600
CACHE_TTL_BATCH_STATS=300

# ============================================
# Webhook
# ============================================
WEBHOOK_RETRY_COUNT=3
WEBHOOK_TIMEOUT=10
WEBHOOK_RETRY_DELAY=900

# ============================================
# File Storage
# ============================================
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=10485760
FILE_RETENTION_DAYS=30

# ============================================
# API
# ============================================
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
EOF
```

Expected: File created at `.env.docker` with all Docker credentials using service names (postgres, redis, rabbitmq, minio).

- [ ] **Step 2: Verify file was created**

```bash
head -20 .env.docker
```

Expected: First 20 lines showing DATABASE_URL with `@postgres:5432` (Docker service name).

---

## Task 3: Update .env.example

**Files:**
- Create/Modify: `.env.example`

Template for developers to copy when setting up the project.

- [ ] **Step 1: Create or update .env.example**

```bash
cat > .env.example << 'EOF'
# ============================================
# Application
# ============================================
APP_NAME=Production Control System
APP_VERSION=1.0.0
DEBUG=true
LOG_LEVEL=INFO

# ============================================
# Database
# ============================================
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/production_control
DATABASE_SYNC_URL=postgresql://postgres:postgres@localhost:5432/production_control

# ============================================
# Redis
# ============================================
REDIS_URL=redis://localhost:6379
REDIS_CACHE_DB=0
REDIS_CELERY_BACKEND_DB=1

# ============================================
# RabbitMQ / Celery Broker
# ============================================
CELERY_BROKER_URL=amqp://admin:admin@localhost:5672//

# ============================================
# MinIO (S3-compatible Storage)
# ============================================
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_BUCKET_REPORTS=reports
MINIO_BUCKET_EXPORTS=exports
MINIO_BUCKET_IMPORTS=imports

# ============================================
# Security
# ============================================
SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ============================================
# Caching TTL (seconds)
# ============================================
CACHE_TTL_DASHBOARD=300
CACHE_TTL_BATCH_LIST=60
CACHE_TTL_BATCH_DETAIL=600
CACHE_TTL_BATCH_STATS=300

# ============================================
# Webhook
# ============================================
WEBHOOK_RETRY_COUNT=3
WEBHOOK_TIMEOUT=10
WEBHOOK_RETRY_DELAY=900

# ============================================
# File Storage
# ============================================
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=10485760
FILE_RETENTION_DAYS=30

# ============================================
# API
# ============================================
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
EOF
```

Expected: File created at `.env.example` with all variables using localhost (for local development).

- [ ] **Step 2: Verify file exists and is readable**

```bash
wc -l .env.example
```

Expected: Around 60-70 lines depending on formatting.

---

## Task 4: Update docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

Add `env_file` directive so docker-compose reads from `.env.docker` instead of hardcoded environment.

- [ ] **Step 1: Read current docker-compose.yml to see structure**

```bash
head -40 docker-compose.yml
```

Expected: You'll see the `api` service with hardcoded environment variables.

- [ ] **Step 2: Update docker-compose.yml to use env_file**

Replace the `environment:` section in all services (api, celery_worker, celery_beat, flower, minio) with `env_file: .env.docker`.

Find these sections in `docker-compose.yml`:
```yaml
services:
  api:
    ...
    environment:
      - DATABASE_URL=...
      - REDIS_URL=...
```

Replace with:
```yaml
services:
  api:
    ...
    env_file: .env.docker
```

Do this for EACH service that has `environment:` (api, celery_worker, celery_beat, flower). Keep health checks as-is.

**Exact changes:**
- Line ~20: Replace api `environment:` block with `env_file: .env.docker`
- Line ~101: Replace celery_worker `environment:` block with `env_file: .env.docker`
- Line ~125: Replace celery_beat `environment:` block with `env_file: .env.docker`
- Line ~150: Replace flower `environment:` block with `env_file: .env.docker`
- Keep minio service as-is (it has hardcoded credentials, optional to change later)

After editing, the structure should look like:
```yaml
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: production_control_api
    ports:
      - "8000:8000"
    depends_on:
      ...
    env_file: .env.docker
    volumes:
      - ./src:/app/src
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Step 3: Verify docker-compose.yml is valid**

```bash
docker-compose config > /dev/null && echo "✓ docker-compose.yml is valid" || echo "✗ Error in docker-compose.yml"
```

Expected: Output "✓ docker-compose.yml is valid"

---

## Task 5: Update alembic/env.py

**Files:**
- Modify: `alembic/env.py`

Change alembic to read database URL from `config.py` instead of `alembic.ini`. This way alembic respects `.env` like the FastAPI app does.

- [ ] **Step 1: Read current alembic/env.py**

```bash
cat alembic/env.py | head -30
```

Expected: You'll see imports and the `run_migrations_*` functions. Look for where `sqlalchemy.url` is read.

- [ ] **Step 2: Update alembic/env.py to import and use config**

Find the section that loads sqlalchemy.url (usually around line 20-30). Replace it with:

```python
from src.core.config import settings

# Get the database URL from Pydantic Settings (reads from .env)
sqlalchemy_url = settings.database_sync_url
```

Then use `sqlalchemy_url` instead of reading from `config.get_section('sqlalchemy')`.

**Full example of what the top of env.py should look like:**

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from src.core.config import settings
from src.core.database import Base

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model's MetaData object for 'autogenerate' support
target_metadata = Base.metadata

# Get database URL from Pydantic Settings (reads from .env)
sqlalchemy_url = settings.database_sync_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=sqlalchemy_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = sqlalchemy_url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Key changes:
- Add `from src.core.config import settings`
- Add `from src.core.database import Base`
- Replace `config.get('sqlalchemy', 'sqlalchemy.url')` with `settings.database_sync_url`
- Use `sqlalchemy_url` in both `run_migrations_*` functions

- [ ] **Step 3: Verify alembic/env.py syntax**

```bash
python -c "import alembic.env; print('✓ alembic/env.py is valid')"
```

Expected: Output "✓ alembic/env.py is valid" (no syntax errors)

---

## Task 6: Update alembic.ini

**Files:**
- Modify: `alembic.ini`

Remove hardcoded `sqlalchemy.url` since it's now read from `config.py` in `env.py`.

- [ ] **Step 1: Find and remove hardcoded sqlalchemy.url**

```bash
grep -n "sqlalchemy.url" alembic.ini
```

Expected: Line number where `sqlalchemy.url = ...` is defined.

- [ ] **Step 2: Comment out or remove the line**

Find the line (e.g., line 60) that says:
```ini
sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/production_control
```

Replace it with:
```ini
# sqlalchemy.url is now loaded from src.core.config.settings in env.py
# This allows alembic to use the same .env file as the FastAPI app
```

- [ ] **Step 3: Verify alembic.ini has no hardcoded database URL**

```bash
grep -E "^sqlalchemy.url" alembic.ini && echo "✗ Still has hardcoded URL" || echo "✓ Hardcoded URL removed"
```

Expected: Output "✓ Hardcoded URL removed"

---

## Task 7: Clean Up database.py

**Files:**
- Modify: `src/core/database.py`

Remove duplicate database connection logic. This file should only contain engine creation and sessionmaker, NOT FastAPI dependencies.

- [ ] **Step 1: Read current database.py**

```bash
cat src/core/database.py
```

Expected: You'll see engine creation, sessionmaker, Base class, and possibly a `get_db()` function.

- [ ] **Step 2: Keep only engine/sessionmaker/Base, remove get_db()**

If `get_db()` exists in this file, DELETE it. The file should look like:

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from src.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Create session factory
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for all ORM models
Base = declarative_base()
```

**After the changes, database.py should have:**
- ✅ Imports
- ✅ Engine creation (using `settings.database_url`)
- ✅ SessionLocal factory
- ✅ Base class
- ❌ NO `get_db()` function

- [ ] **Step 3: Verify no get_db function**

```bash
grep -n "def get_db" src/core/database.py && echo "✗ Still has get_db()" || echo "✓ get_db() removed"
```

Expected: Output "✓ get_db() removed"

---

## Task 8: Verify dependencies.py has Single get_db()

**Files:**
- Verify: `src/core/dependencies.py`

Ensure `get_db()` is defined here (and ONLY here), not duplicated elsewhere.

- [ ] **Step 1: Read dependencies.py**

```bash
cat src/core/dependencies.py
```

Expected: You'll see `get_db()` as an async generator for FastAPI dependency injection.

- [ ] **Step 2: Verify get_db() function exists**

```bash
grep -n "async def get_db" src/core/dependencies.py
```

Expected: One result showing the line number where `get_db()` is defined.

**If get_db() doesn't exist, add it:**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import SessionLocal
from fastapi import Depends

async def get_db() -> AsyncSession:
    """Dependency for getting database session in FastAPI routes."""
    async with SessionLocal() as session:
        yield session
```

- [ ] **Step 3: Verify get_db is only defined once**

```bash
grep -r "def get_db" src/ --include="*.py" | wc -l
```

Expected: Output is exactly 1 (only in dependencies.py)

---

## Task 9: Update .gitignore

**Files:**
- Modify: `.gitignore`

Ensure `.env*` files are ignored so credentials never leak to git.

- [ ] **Step 1: Check current .gitignore**

```bash
grep "\.env" .gitignore
```

Expected: You should see `.env*` or `.env` pattern.

- [ ] **Step 2: If not present, add it**

If `.env` is not in .gitignore, add these lines:

```bash
cat >> .gitignore << 'EOF'

# Environment files (contain credentials)
.env
.env.*
!.env.example
EOF
```

This ensures:
- ✅ `.env` is ignored
- ✅ `.env.docker` is ignored
- ✅ `.env.local` is ignored
- ✅ But `.env.example` IS committed (as a template)

- [ ] **Step 3: Verify .env files are ignored**

```bash
git check-ignore .env.docker .env.local .env.example
```

Expected: 
```
.env.docker
.env.local
(nothing for .env.example, meaning it's NOT ignored)
```

---

## Task 10: Test Local Setup

**Files:**
- Test: `.env.local` setup
- Test: Local `uvicorn` run
- Test: `pytest` execution

Verify the refactoring works for local development.

- [ ] **Step 1: Create .env.local for local development**

```bash
cp .env.example .env.local
```

- [ ] **Step 2: Edit .env.local with your actual local database**

```bash
# Edit with your text editor
nano .env.local
# Or use sed to update database URLs
```

Make sure:
- `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/production_control`
- `DATABASE_SYNC_URL=postgresql://postgres:postgres@localhost:5432/production_control`
- `REDIS_URL=redis://localhost:6379` (or your Redis location)
- `CELERY_BROKER_URL=amqp://admin:admin@localhost:5672//` (or your RabbitMQ)

- [ ] **Step 3: Load .env.local and test uvicorn**

```bash
# Load environment
export $(cat .env.local | grep -v '#' | xargs)

# Run uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Expected: 
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Leave it running, then in another terminal test the health endpoint.

- [ ] **Step 4: Test health endpoint in another terminal**

```bash
curl http://localhost:8000/health
```

Expected output:
```json
{"status":"ok","version":"1.0.0"}
```

If successful, kill uvicorn (Ctrl+C in first terminal).

- [ ] **Step 5: Test pytest**

```bash
export $(cat .env.local | grep -v '#' | xargs)
pytest tests/ -v
```

Expected: Tests run and pass (or fail with clear test errors, not database connection errors).

---

## Task 11: Test Docker Compose Setup

**Files:**
- Test: Docker Compose startup
- Test: Alembic migrations
- Test: API health check

Verify the refactoring works in Docker environment.

- [ ] **Step 1: Verify .env.docker exists**

```bash
ls -la .env.docker
```

Expected: File exists with proper permissions.

- [ ] **Step 2: Start Docker Compose**

```bash
docker-compose up -d
```

Expected:
```
Creating production_control_db ... done
Creating production_control_redis ... done
Creating production_control_rabbitmq ... done
Creating production_control_minio ... done
Creating production_control_api ... done
Creating production_control_worker ... done
Creating production_control_beat ... done
Creating production_control_flower ... done
```

- [ ] **Step 3: Wait for services to be healthy**

```bash
sleep 10
docker-compose ps
```

Expected: All services show `healthy` or `running` status.

- [ ] **Step 4: Test API health endpoint**

```bash
curl http://localhost:8000/health
```

Expected output:
```json
{"status":"ok","version":"1.0.0"}
```

- [ ] **Step 5: Check Flower (Celery monitoring)**

Open browser to `http://localhost:5555`

Expected: Flower dashboard loads, showing worker status.

- [ ] **Step 6: Stop Docker Compose**

```bash
docker-compose down
```

Expected: All containers stopped.

---

## Task 12: Commit Changes

**Files:**
- Commit: All modified and new files

Create a clean git commit with all refactoring changes.

- [ ] **Step 1: Check git status**

```bash
git status
```

Expected: Untracked/modified files listed (docker-compose.yml, alembic/, .env.docker, .env.example, src/core/, .gitignore).

- [ ] **Step 2: Stage all changes**

```bash
git add docker-compose.yml alembic/ .env.docker .env.example src/core/ .gitignore
```

- [ ] **Step 3: Create commit**

```bash
git commit -m "refactor: move credentials to .env, remove db connection duplication

- Move docker-compose credentials to .env.docker file
- Update alembic/env.py to read from Pydantic Settings config
- Remove hardcoded sqlalchemy.url from alembic.ini
- Remove duplicate get_db() from database.py (now only in dependencies.py)
- Create .env.example template for local setup
- Update .gitignore to ignore .env* files
- Ensure .env.example is committed as a template

This makes the application production-ready:
- All secrets are environment-based, not hardcoded
- Single source of truth for database initialization
- Works seamlessly across dev/test/docker environments
- Alembic respects .env like the FastAPI app does"
```

- [ ] **Step 4: Verify commit created**

```bash
git log -1 --oneline
```

Expected: Your new commit appears at the top.

---

## Success Criteria Checklist

After all tasks complete, verify:

- [ ] No hardcoded credentials in `docker-compose.yml`
- [ ] No hardcoded credentials in `alembic.ini`
- [ ] `alembic/env.py` reads from `config.py` using `settings.database_sync_url`
- [ ] `database.py` has no `get_db()` function
- [ ] `dependencies.py` has `get_db()` function (and it's the ONLY place)
- [ ] `.env.docker` exists with Docker service credentials
- [ ] `.env.example` exists as a template
- [ ] `.gitignore` includes `.env*` (except `.env.example`)
- [ ] Local development works: `uvicorn src.main:app --reload`
- [ ] Tests pass: `pytest tests/`
- [ ] Docker Compose works: `docker-compose up -d` → health check passes
- [ ] All changes committed with clear message
