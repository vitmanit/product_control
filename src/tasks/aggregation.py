import asyncio
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.celery_app import celery_app
from src.core.database import AsyncSessionLocal
from src.domain.models.product import Product


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _aggregate_products(batch_id: int, unique_codes: list[str], task) -> dict:
    async with AsyncSessionLocal() as session:
        aggregated = 0
        failed = []
        total = len(unique_codes)

        for i, code in enumerate(unique_codes):
            query = select(Product).where(Product.unique_code == code)
            result = await session.execute(query)
            product = result.scalar_one_or_none()

            if product is None:
                failed.append({"code": code, "reason": "not found"})
            elif product.batch_id != batch_id:
                failed.append({"code": code, "reason": "wrong batch"})
            elif product.is_aggregated:
                failed.append({"code": code, "reason": "already aggregated"})
            else:
                product.is_aggregated = True
                product.aggregated_at = datetime.utcnow()
                aggregated += 1

            # Обновляем прогресс каждые 10 единиц
            if (i + 1) % 10 == 0:
                task.update_state(
                    state="PROGRESS",
                    meta={"current": i + 1, "total": total, "progress": round((i + 1) / total * 100)},
                )

        await session.commit()

    return {
        "success": True,
        "total": total,
        "aggregated": aggregated,
        "failed": len(failed),
        "errors": failed,
    }


@celery_app.task(bind=True, max_retries=3, name="src.tasks.aggregation.aggregate_products_batch")
def aggregate_products_batch(self, batch_id: int, unique_codes: list[str], user_id: int | None = None):
    return _run_async(_aggregate_products(batch_id, unique_codes, self))
