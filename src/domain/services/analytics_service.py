from datetime import datetime, date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache import RedisCache
from src.core.config import settings
from src.core.exceptions import NotFoundError
from src.domain.models.batch import Batch
from src.domain.models.product import Product
from src.domain.models.work_center import WorkCenter
from src.domain.repositories.batch_repository import BatchRepository
from src.domain.repositories.product_repository import ProductRepository


class AnalyticsService:
    def __init__(self, session: AsyncSession, cache: RedisCache):
        self.session = session
        self.cache = cache
        self.batch_repo = BatchRepository(session)
        self.product_repo = ProductRepository(session)

    async def get_dashboard_stats(self) -> dict:
        cached = await self.cache.get("dashboard_stats")
        if cached:
            return cached

        # Summary
        total_batches = (await self.session.execute(
            select(func.count()).select_from(Batch)
        )).scalar()
        active_batches = (await self.session.execute(
            select(func.count()).select_from(Batch).where(Batch.is_closed == False)
        )).scalar()
        closed_batches = total_batches - active_batches

        total_products = (await self.session.execute(
            select(func.count()).select_from(Product)
        )).scalar()
        aggregated_products = (await self.session.execute(
            select(func.count()).select_from(Product).where(Product.is_aggregated == True)
        )).scalar()

        agg_rate = round((aggregated_products / total_products * 100), 2) if total_products > 0 else 0

        # Today stats
        today = date.today()
        today_batches_created = (await self.session.execute(
            select(func.count()).select_from(Batch).where(
                func.date(Batch.created_at) == today
            )
        )).scalar()
        today_batches_closed = (await self.session.execute(
            select(func.count()).select_from(Batch).where(
                func.date(Batch.closed_at) == today
            )
        )).scalar()
        today_products_added = (await self.session.execute(
            select(func.count()).select_from(Product).where(
                func.date(Product.created_at) == today
            )
        )).scalar()
        today_products_aggregated = (await self.session.execute(
            select(func.count()).select_from(Product).where(
                func.date(Product.aggregated_at) == today
            )
        )).scalar()

        # By shift
        shift_stats_q = (
            select(
                Batch.shift,
                func.count(Batch.id).label("batches"),
            )
            .group_by(Batch.shift)
        )
        shift_results = (await self.session.execute(shift_stats_q)).all()
        by_shift = {}
        for row in shift_results:
            products_in_shift = (await self.session.execute(
                select(func.count()).select_from(Product)
                .join(Batch)
                .where(Batch.shift == row.shift)
            )).scalar()
            agg_in_shift = (await self.session.execute(
                select(func.count()).select_from(Product)
                .join(Batch)
                .where(Batch.shift == row.shift, Product.is_aggregated == True)
            )).scalar()
            by_shift[row.shift] = {
                "batches": row.batches,
                "products": products_in_shift,
                "aggregated": agg_in_shift,
            }

        # Top work centers
        top_wc_q = (
            select(
                WorkCenter.identifier,
                WorkCenter.name,
                func.count(Batch.id).label("batches_count"),
            )
            .join(Batch, Batch.work_center_id == WorkCenter.id)
            .group_by(WorkCenter.id, WorkCenter.identifier, WorkCenter.name)
            .order_by(func.count(Batch.id).desc())
            .limit(5)
        )
        top_wc = (await self.session.execute(top_wc_q)).all()
        top_work_centers = []
        for wc in top_wc:
            products_count = (await self.session.execute(
                select(func.count()).select_from(Product)
                .join(Batch)
                .join(WorkCenter)
                .where(WorkCenter.identifier == wc.identifier)
            )).scalar()
            agg_count = (await self.session.execute(
                select(func.count()).select_from(Product)
                .join(Batch)
                .join(WorkCenter)
                .where(WorkCenter.identifier == wc.identifier, Product.is_aggregated == True)
            )).scalar()
            top_work_centers.append({
                "id": wc.identifier,
                "name": wc.name,
                "batches_count": wc.batches_count,
                "products_count": products_count,
                "aggregation_rate": round((agg_count / products_count * 100), 2) if products_count > 0 else 0,
            })

        result = {
            "summary": {
                "total_batches": total_batches,
                "active_batches": active_batches,
                "closed_batches": closed_batches,
                "total_products": total_products,
                "aggregated_products": aggregated_products,
                "aggregation_rate": agg_rate,
            },
            "today": {
                "batches_created": today_batches_created,
                "batches_closed": today_batches_closed,
                "products_added": today_products_added,
                "products_aggregated": today_products_aggregated,
            },
            "by_shift": by_shift,
            "top_work_centers": top_work_centers,
            "cached_at": datetime.utcnow().isoformat() + "Z",
        }

        await self.cache.set("dashboard_stats", result, ttl=settings.cache_ttl_dashboard)
        return result

    async def get_batch_statistics(self, batch_id: int) -> dict:
        cached = await self.cache.get(f"batch_statistics:{batch_id}")
        if cached:
            return cached

        batch = await self.batch_repo.get_with_products(batch_id)
        if not batch:
            raise NotFoundError(f"Batch {batch_id} not found")

        stats = await self.product_repo.count_by_batch(batch_id)

        shift_duration = (batch.shift_end - batch.shift_start).total_seconds() / 3600
        elapsed = (datetime.utcnow() - batch.shift_start.replace(tzinfo=None)).total_seconds() / 3600
        elapsed = min(elapsed, shift_duration)
        products_per_hour = round(stats["aggregated"] / elapsed, 2) if elapsed > 0 else 0

        estimated_remaining = (
            (stats["remaining"] / products_per_hour) if products_per_hour > 0 else None
        )

        result = {
            "batch_info": {
                "id": batch.id,
                "batch_number": batch.batch_number,
                "batch_date": str(batch.batch_date),
                "is_closed": batch.is_closed,
            },
            "production_stats": stats,
            "timeline": {
                "shift_duration_hours": round(shift_duration, 2),
                "elapsed_hours": round(elapsed, 2),
                "products_per_hour": products_per_hour,
                "estimated_remaining_hours": round(estimated_remaining, 2) if estimated_remaining else None,
            },
            "team_performance": {
                "team": batch.team,
                "avg_products_per_hour": products_per_hour,
            },
        }

        await self.cache.set(f"batch_statistics:{batch_id}", result, ttl=settings.cache_ttl_batch_stats)
        return result

    async def compare_batches(self, batch_ids: list[int]) -> dict:
        comparison = []
        for bid in batch_ids:
            batch = await self.batch_repo.get_with_products(bid)
            if not batch:
                continue
            stats = await self.product_repo.count_by_batch(bid)
            duration = (batch.shift_end - batch.shift_start).total_seconds() / 3600
            pph = round(stats["aggregated"] / duration, 2) if duration > 0 else 0
            comparison.append({
                "batch_id": batch.id,
                "batch_number": batch.batch_number,
                "total_products": stats["total_products"],
                "aggregated": stats["aggregated"],
                "rate": stats["aggregation_rate"],
                "duration_hours": round(duration, 2),
                "products_per_hour": pph,
            })

        avg_rate = round(sum(c["rate"] for c in comparison) / len(comparison), 2) if comparison else 0
        avg_pph = round(sum(c["products_per_hour"] for c in comparison) / len(comparison), 2) if comparison else 0

        return {
            "comparison": comparison,
            "average": {
                "aggregation_rate": avg_rate,
                "products_per_hour": avg_pph,
            },
        }
