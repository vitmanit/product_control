from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db, get_cache
from src.core.cache import RedisCache
from src.domain.services.analytics_service import AnalyticsService

router = APIRouter(tags=["analytics"])


class CompareBatchesRequest(BaseModel):
    batch_ids: list[int]


@router.get("/analytics/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
):
    service = AnalyticsService(db, cache)
    return await service.get_dashboard_stats()


@router.get("/batches/{batch_id}/statistics")
async def get_batch_statistics(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
):
    service = AnalyticsService(db, cache)
    return await service.get_batch_statistics(batch_id)


@router.post("/analytics/compare-batches")
async def compare_batches(
    data: CompareBatchesRequest,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
):
    service = AnalyticsService(db, cache)
    return await service.compare_batches(data.batch_ids)
