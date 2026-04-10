from datetime import datetime
from typing import Sequence

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.product import Product
from src.domain.repositories.base_repository import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession):
        super().__init__(Product, session)

    async def get_by_unique_code(self, unique_code: str) -> Product | None:
        query = select(Product).where(Product.unique_code == unique_code)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_batch_id(self, batch_id: int) -> Sequence[Product]:
        query = select(Product).where(Product.batch_id == batch_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def aggregate(self, product: Product) -> Product:
        product.is_aggregated = True
        product.aggregated_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def bulk_aggregate(self, batch_id: int, unique_codes: list[str]) -> dict:
        aggregated = 0
        failed = []

        for code in unique_codes:
            product = await self.get_by_unique_code(code)
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

        await self.session.flush()
        return {
            "total": len(unique_codes),
            "aggregated": aggregated,
            "failed": len(failed),
            "errors": failed,
        }

    async def count_by_batch(self, batch_id: int) -> dict:
        total_q = select(func.count()).select_from(Product).where(Product.batch_id == batch_id)
        agg_q = select(func.count()).select_from(Product).where(
            Product.batch_id == batch_id,
            Product.is_aggregated == True,
        )
        total = (await self.session.execute(total_q)).scalar()
        aggregated = (await self.session.execute(agg_q)).scalar()
        return {
            "total_products": total,
            "aggregated": aggregated,
            "remaining": total - aggregated,
            "aggregation_rate": round((aggregated / total * 100), 2) if total > 0 else 0,
        }
