import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select, func, update

from src.celery_app import celery_app
from src.core.database import AsyncSessionLocal
from src.core.config import settings
from src.core.cache import RedisCache
from src.domain.models.batch import Batch
from src.domain.models.product import Product
from src.domain.models.webhook import WebhookDelivery, WebhookSubscription
from src.storage.minio_service import minio_service


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="src.tasks.scheduled.auto_close_expired_batches")
def auto_close_expired_batches():
    async def _run():
        async with AsyncSessionLocal() as session:
            query = select(Batch).where(
                Batch.is_closed == False,
                Batch.shift_end < func.now(),
            )
            result = await session.execute(query)
            expired = result.scalars().all()

            count = 0
            for batch in expired:
                batch.is_closed = True
                batch.closed_at = datetime.utcnow()
                count += 1

            await session.commit()
            return {"closed": count}

    return _run_async(_run())


@celery_app.task(name="src.tasks.scheduled.cleanup_old_files")
def cleanup_old_files():
    cutoff = datetime.utcnow() - timedelta(days=settings.file_retention_days)
    deleted = 0

    for bucket in [settings.minio_bucket_reports, settings.minio_bucket_exports]:
        objects = minio_service.list_files(bucket)
        for obj in objects:
            if obj.last_modified and obj.last_modified.replace(tzinfo=None) < cutoff:
                minio_service.delete_file(bucket, obj.object_name)
                deleted += 1

    return {"deleted": deleted}


@celery_app.task(name="src.tasks.scheduled.update_cached_statistics")
def update_cached_statistics():
    async def _run():
        cache = RedisCache()
        await cache.init()

        async with AsyncSessionLocal() as session:
            total_batches = (await session.execute(
                select(func.count()).select_from(Batch)
            )).scalar()
            active_batches = (await session.execute(
                select(func.count()).select_from(Batch).where(Batch.is_closed == False)
            )).scalar()
            total_products = (await session.execute(
                select(func.count()).select_from(Product)
            )).scalar()
            aggregated_products = (await session.execute(
                select(func.count()).select_from(Product).where(Product.is_aggregated == True)
            )).scalar()

        stats = {
            "summary": {
                "total_batches": total_batches,
                "active_batches": active_batches,
                "closed_batches": total_batches - active_batches,
                "total_products": total_products,
                "aggregated_products": aggregated_products,
                "aggregation_rate": round((aggregated_products / total_products * 100), 2) if total_products > 0 else 0,
            },
            "cached_at": datetime.utcnow().isoformat() + "Z",
        }

        await cache.set("dashboard_stats", stats, ttl=settings.cache_ttl_dashboard)
        await cache.close()
        return stats

    return _run_async(_run())


@celery_app.task(name="src.tasks.scheduled.retry_failed_webhooks")
def retry_failed_webhooks():
    from src.tasks.webhooks import send_webhook_delivery

    async def _run():
        async with AsyncSessionLocal() as session:
            query = (
                select(WebhookDelivery)
                .where(WebhookDelivery.status == "failed")
                .join(WebhookSubscription)
                .where(WebhookSubscription.is_active == True)
            )
            result = await session.execute(query)
            failed = result.scalars().all()

            retried = 0
            for delivery in failed:
                if delivery.attempts < delivery.subscription.retry_count:
                    send_webhook_delivery.delay(delivery.id)
                    retried += 1

            return {"retried": retried}

    return _run_async(_run())
