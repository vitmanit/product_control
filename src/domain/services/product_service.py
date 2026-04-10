from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache import RedisCache
from src.core.exceptions import NotFoundError, ConflictError
from src.domain.models.product import Product
from src.domain.repositories.product_repository import ProductRepository
from src.domain.repositories.batch_repository import BatchRepository


class ProductService:
    def __init__(self, session: AsyncSession, cache: RedisCache):
        self.session = session
        self.repo = ProductRepository(session)
        self.batch_repo = BatchRepository(session)
        self.cache = cache

    async def add_product(self, unique_code: str, batch_id: int) -> Product:
        batch = await self.batch_repo.get_by_id(batch_id)
        if not batch:
            raise NotFoundError(f"Batch {batch_id} not found")

        existing = await self.repo.get_by_unique_code(unique_code)
        if existing:
            raise ConflictError(f"Product with code {unique_code} already exists")

        product = await self.repo.create(unique_code=unique_code, batch_id=batch_id)
        await self._invalidate_cache(batch_id)
        return product

    async def aggregate_product(self, batch_id: int, unique_codes: list[str]) -> dict:
        batch = await self.batch_repo.get_by_id(batch_id)
        if not batch:
            raise NotFoundError(f"Batch {batch_id} not found")

        result = await self.repo.bulk_aggregate(batch_id, unique_codes)
        result["success"] = True
        await self._invalidate_cache(batch_id)
        return result

    async def _invalidate_cache(self, batch_id: int):
        await self.cache.delete(f"batch_detail:{batch_id}")
        await self.cache.delete(f"batch_statistics:{batch_id}")
        await self.cache.delete("dashboard_stats")
