from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.cache import cache
from src.api.v1.routers import batches, products, tasks, webhooks, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await cache.init()
    try:
        from src.storage.minio_service import minio_service
        minio_service.ensure_buckets()
    except Exception as e:
        print(f"MinIO init warning: {e}")
    yield
    # Shutdown
    await cache.close()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роутеры
app.include_router(batches.router, prefix=settings.api_v1_prefix)
app.include_router(products.router, prefix=settings.api_v1_prefix)
app.include_router(tasks.router, prefix=settings.api_v1_prefix)
app.include_router(webhooks.router, prefix=settings.api_v1_prefix)
app.include_router(analytics.router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.app_version}
