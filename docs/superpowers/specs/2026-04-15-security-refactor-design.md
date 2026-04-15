# Quick Security Fix Refactor Design

**Date:** 2026-04-15  
**Scope:** Security credentials management, code deduplication, environment configuration  
**Estimated Time:** 2-3 hours  

---

## Problem Statement

Currently, the project has three security and code quality issues:

1. **Hardcoded Credentials** — `docker-compose.yml` and `alembic.ini` contain hardcoded database credentials instead of reading from `.env`
2. **Code Duplication** — Database connection function is defined in both `database.py` and `dependencies.py`
3. **Config Management** — No clear separation between environment configs (dev/test/prod)

These issues create:
- ⚠️ Security risk (credentials in version control)
- 🔄 Maintenance burden (changes in two places)
- 🤔 Unclear architecture (where does DB initialization actually happen?)

---

## Solution Overview

Move all credentials to `.env` files, eliminate code duplication, and establish clear configuration management. This is a **non-breaking change** — the application behavior stays the same, only the configuration source changes.

### Key Changes

#### 1. **docker-compose.yml** 
```yaml
# Change from hardcoded environment vars to:
env_file: .env.docker
```

**Details:**
- Create `.env.docker` with production Docker credentials
- docker-compose reads from this file instead of inline environment
- File is gitignored

#### 2. **alembic.ini**
```ini
# Change from:
sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/production_control

# To:
sqlalchemy.url = 
```

**Details:**
- Modify `alembic/env.py` to read from `config.py` instead of `alembic.ini`
- Use existing `settings.database_sync_url` from Pydantic Settings
- This way alembic respects `.env` automatically

#### 3. **database.py → Simplify**
- Keep only: engine creation, sessionmaker, Base class
- Remove any `get_db()` function if present (it belongs in dependencies.py)

#### 4. **dependencies.py → Single Source of Truth**
- Keep: `get_db()` async generator for FastAPI dependency injection
- Remove: any database initialization logic
- This is the ONLY place FastAPI gets database sessions

#### 5. **.env Files Structure**
```
.env.example          # Template with all variables
.env.local           # Local development (git ignored)
.env.docker          # Docker Compose credentials (git ignored)
.env.test            # Test database URL (git ignored, optional)
```

---

## File Changes Matrix

| File | Change | Why |
|------|--------|-----|
| `docker-compose.yml` | Add `env_file: .env.docker` | Read secrets from file, not hardcoded |
| `alembic/env.py` | Import config and read `database_sync_url` | Alembic respects .env like FastAPI does |
| `alembic.ini` | Remove hardcoded `sqlalchemy.url` | Moved to code (config.py) |
| `database.py` | Remove `get_db()` if present | Single source of truth in dependencies.py |
| `dependencies.py` | Ensure `get_db()` is only DB function | Centralize FastAPI DB dependency |
| `.env.example` | Add/verify all required variables | Template for setup |
| `.gitignore` | Verify `.env*` entries | Prevent credential leaks |

---

## Environment Configuration

### Local Development
```bash
cp .env.example .env.local
# Edit with your local database/redis/etc
export $(cat .env.local | grep -v '#' | xargs)
uvicorn src.main:app --reload
```

### Docker Compose
```bash
cp .env.example .env.docker
# Edit with Docker container names (postgres:5432, redis:6379, etc)
docker-compose up -d
```

### Tests
```bash
# Use TEST_DATABASE_URL from existing conftest.py
pytest  # Tests use hardcoded test DB URL for isolation
```

---

## Implementation Order

1. Create `.env.docker` with production Docker credentials
2. Update `alembic/env.py` to read from config
3. Remove `sqlalchemy.url` line from `alembic.ini`
4. Update `docker-compose.yml` to use `env_file`
5. Clean up `database.py` (remove `get_db()` if present)
6. Verify `dependencies.py` has single `get_db()` function
7. Test: `docker-compose up -d && alembic upgrade head`
8. Test: Local `uvicorn` with `.env.local`
9. Test: `pytest` still works with test database

---

## What Stays the Same

- ✅ API behavior unchanged
- ✅ Database models unchanged
- ✅ Celery configuration unchanged
- ✅ MinIO/Redis/RabbitMQ unchanged
- ✅ Tests still pass
- ✅ CLAUDE.md guidance still valid

---

## Success Criteria

✅ No hardcoded credentials in repository  
✅ `docker-compose up` works with `.env.docker`  
✅ `alembic upgrade head` works with `.env.local`  
✅ `uvicorn src.main:app --reload` works with `.env.local`  
✅ `pytest` passes with test database  
✅ No code duplication for database connection  
✅ Clear one-place-only for DB initialization  

---

## Risk Assessment

**Risk Level:** 🟢 **LOW**

- Changes are configuration-only, not logic
- Existing code patterns stay the same
- Full rollback: revert credentials back to hardcoded (if needed)
- Tests catch any breakage immediately

---

## Dependencies & Notes

- Requires `.env` files to be created (simple copy of `.env.example`)
- No new dependencies needed
- Works with existing Docker setup
- Backward compatible (can switch back if needed)
