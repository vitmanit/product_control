import asyncio
from datetime import datetime

import httpx

from src.celery_app import celery_app
from src.core.database import AsyncSessionLocal
from src.domain.models.webhook import WebhookDelivery, WebhookSubscription
from src.utils.hmac_utils import generate_signature


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _send_delivery(delivery_id: int) -> dict:
    async with AsyncSessionLocal() as session:
        delivery = await session.get(WebhookDelivery, delivery_id)
        if not delivery:
            return {"success": False, "error": "Delivery not found"}

        subscription = await session.get(WebhookSubscription, delivery.subscription_id)
        if not subscription:
            return {"success": False, "error": "Subscription not found"}

        signature = generate_signature(delivery.payload, subscription.secret_key)

        delivery.attempts += 1

        try:
            async with httpx.AsyncClient(timeout=subscription.timeout) as client:
                response = await client.post(
                    subscription.url,
                    json=delivery.payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": signature,
                        "X-Webhook-Event": delivery.event_type,
                    },
                )

            delivery.response_status = response.status_code
            delivery.response_body = response.text[:1000]

            if 200 <= response.status_code < 300:
                delivery.status = "success"
                delivery.delivered_at = datetime.utcnow()
            else:
                delivery.status = "failed"
                delivery.error_message = f"HTTP {response.status_code}"

        except Exception as e:
            delivery.status = "failed"
            delivery.error_message = str(e)[:500]

        await session.commit()

        return {
            "success": delivery.status == "success",
            "delivery_id": delivery_id,
            "status": delivery.status,
            "attempts": delivery.attempts,
        }


@celery_app.task(bind=True, max_retries=3, name="src.tasks.webhooks.send_webhook_delivery")
def send_webhook_delivery(self, delivery_id: int):
    result = _run_async(_send_delivery(delivery_id))

    if not result.get("success") and self.request.retries < self.max_retries:
        raise self.retry(countdown=60 * (2 ** self.request.retries))

    return result
