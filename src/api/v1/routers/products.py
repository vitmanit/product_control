from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db, get_cache
from src.core.cache import RedisCache
from src.domain.services.product_service import ProductService
from src.domain.services.webhook_service import WebhookService
from src.api.v1.schemas.product import ProductCreate, ProductResponse, AggregateRequest, AggregateResult

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProductResponse)
async def add_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
):
    service = ProductService(db, cache)
    return await service.add_product(data.unique_code, data.batch_id)


@router.post(
    "/batches/{batch_id}/aggregate",
    response_model=AggregateResult,
    tags=["batches"],
)
async def aggregate_products(
    batch_id: int,
    data: AggregateRequest,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
):
    service = ProductService(db, cache)
    result = await service.aggregate_product(batch_id, data.unique_codes)

    # Webhook
    webhook_service = WebhookService(db)
    for code in data.unique_codes:
        delivery_ids = await webhook_service.trigger_event("product_aggregated", {
            "unique_code": code,
            "batch_id": batch_id,
        })
        from src.tasks.webhooks import send_webhook_delivery
        for did in delivery_ids:
            send_webhook_delivery.delay(did)

    return AggregateResult(**result)
