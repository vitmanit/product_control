from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.domain.models.webhook import WebhookSubscription, WebhookDelivery
from src.domain.repositories.webhook_repository import (
    WebhookSubscriptionRepository,
    WebhookDeliveryRepository,
)


class WebhookService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.sub_repo = WebhookSubscriptionRepository(session)
        self.delivery_repo = WebhookDeliveryRepository(session)

    async def create_subscription(self, **kwargs) -> WebhookSubscription:
        return await self.sub_repo.create(**kwargs)

    async def list_subscriptions(self, offset: int = 0, limit: int = 20):
        return await self.sub_repo.get_all_subscriptions(offset, limit)

    async def get_subscription(self, webhook_id: int) -> WebhookSubscription:
        sub = await self.sub_repo.get_by_id(webhook_id)
        if not sub:
            raise NotFoundError(f"Webhook subscription {webhook_id} not found")
        return sub

    async def update_subscription(self, webhook_id: int, **kwargs) -> WebhookSubscription:
        sub = await self.get_subscription(webhook_id)
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        return await self.sub_repo.update(sub, **update_data)

    async def delete_subscription(self, webhook_id: int) -> None:
        sub = await self.get_subscription(webhook_id)
        await self.sub_repo.delete(sub)

    async def get_deliveries(self, webhook_id: int, offset: int = 0, limit: int = 20):
        await self.get_subscription(webhook_id)
        return await self.delivery_repo.get_by_subscription(webhook_id, offset, limit)

    async def trigger_event(self, event_type: str, data: dict) -> list[int]:
        """Создаёт WebhookDelivery для всех активных подписок на событие и возвращает их ID."""
        subscriptions = await self.sub_repo.get_active_by_event(event_type)
        delivery_ids = []

        for sub in subscriptions:
            payload = {
                "event": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            delivery = await self.delivery_repo.create(
                subscription_id=sub.id,
                event_type=event_type,
                payload=payload,
                status="pending",
            )
            delivery_ids.append(delivery.id)

        return delivery_ids
