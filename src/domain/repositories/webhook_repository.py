from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.webhook import WebhookSubscription, WebhookDelivery
from src.domain.repositories.base_repository import BaseRepository


class WebhookSubscriptionRepository(BaseRepository[WebhookSubscription]):
    def __init__(self, session: AsyncSession):
        super().__init__(WebhookSubscription, session)

    async def get_active_by_event(self, event_type: str) -> Sequence[WebhookSubscription]:
        query = select(WebhookSubscription).where(
            WebhookSubscription.is_active == True,
            WebhookSubscription.events.any(event_type),
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_all_subscriptions(
        self, offset: int = 0, limit: int = 20
    ) -> tuple[Sequence[WebhookSubscription], int]:
        count_q = select(func.count()).select_from(WebhookSubscription)
        total = (await self.session.execute(count_q)).scalar()

        query = (
            select(WebhookSubscription)
            .order_by(WebhookSubscription.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        items = result.scalars().all()
        return items, total


class WebhookDeliveryRepository(BaseRepository[WebhookDelivery]):
    def __init__(self, session: AsyncSession):
        super().__init__(WebhookDelivery, session)

    async def get_by_subscription(
        self, subscription_id: int, offset: int = 0, limit: int = 20
    ) -> tuple[Sequence[WebhookDelivery], int]:
        count_q = (
            select(func.count())
            .select_from(WebhookDelivery)
            .where(WebhookDelivery.subscription_id == subscription_id)
        )
        total = (await self.session.execute(count_q)).scalar()

        query = (
            select(WebhookDelivery)
            .where(WebhookDelivery.subscription_id == subscription_id)
            .order_by(WebhookDelivery.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        items = result.scalars().all()
        return items, total

    async def get_failed_deliveries(self) -> Sequence[WebhookDelivery]:
        query = (
            select(WebhookDelivery)
            .where(WebhookDelivery.status == "failed")
            .join(WebhookSubscription)
            .where(WebhookSubscription.is_active == True)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
