from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db
from src.domain.services.webhook_service import WebhookService
from src.api.v1.schemas.webhook import (
    WebhookCreate, WebhookUpdate, WebhookResponse, WebhookDeliveryResponse,
)
from src.api.v1.schemas.common import PaginatedResponse

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=WebhookResponse)
async def create_webhook(
    data: WebhookCreate,
    db: AsyncSession = Depends(get_db),
):
    service = WebhookService(db)
    return await service.create_subscription(**data.model_dump())


@router.get("", response_model=PaginatedResponse[WebhookResponse])
async def list_webhooks(
    offset: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    service = WebhookService(db)
    items, total = await service.list_subscriptions(offset, limit)
    return PaginatedResponse(items=items, total=total, offset=offset, limit=limit)


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: int,
    data: WebhookUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = WebhookService(db)
    return await service.update_subscription(webhook_id, **data.model_dump(exclude_unset=True))


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = WebhookService(db)
    await service.delete_subscription(webhook_id)


@router.get("/{webhook_id}/deliveries", response_model=PaginatedResponse[WebhookDeliveryResponse])
async def get_deliveries(
    webhook_id: int,
    offset: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    service = WebhookService(db)
    items, total = await service.get_deliveries(webhook_id, offset, limit)
    return PaginatedResponse(items=items, total=total, offset=offset, limit=limit)
