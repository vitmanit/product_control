from datetime import datetime, date
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache import RedisCache
from src.core.exceptions import NotFoundError, ConflictError
from src.domain.models.batch import Batch
from src.domain.models.work_center import WorkCenter
from src.domain.repositories.batch_repository import BatchRepository
from src.api.v1.schemas.batch import BatchCreateItem, BatchUpdate


class BatchService:
    def __init__(self, session: AsyncSession, cache: RedisCache):
        self.session = session
        self.repo = BatchRepository(session)
        self.cache = cache

    async def _get_or_create_work_center(self, identifier: str, name: str) -> WorkCenter:
        query = select(WorkCenter).where(WorkCenter.identifier == identifier)
        result = await self.session.execute(query)
        wc = result.scalar_one_or_none()
        if wc is None:
            wc = WorkCenter(identifier=identifier, name=name)
            self.session.add(wc)
            await self.session.flush()
            await self.session.refresh(wc)
        return wc

    async def create_batches(self, items: list[BatchCreateItem]) -> list[Batch]:
        created = []
        for item in items:
            wc = await self._get_or_create_work_center(
                identifier=item.work_center_identifier,
                name=item.work_center_name,
            )

            existing = await self.repo.get_by_number_and_date(item.batch_number, item.batch_date)
            if existing:
                raise ConflictError(
                    f"Batch with number {item.batch_number} and date {item.batch_date} already exists"
                )

            batch = await self.repo.create(
                is_closed=item.status_closed,
                closed_at=datetime.utcnow() if item.status_closed else None,
                task_description=item.task_description,
                work_center_id=wc.id,
                shift=item.shift,
                team=item.team,
                batch_number=item.batch_number,
                batch_date=item.batch_date,
                nomenclature=item.nomenclature,
                ekn_code=item.ekn_code,
                shift_start=item.shift_start,
                shift_end=item.shift_end,
            )
            created.append(batch)

        await self._invalidate_list_cache()
        return created

    async def get_batch(self, batch_id: int) -> Batch:
        cached = await self.cache.get(f"batch_detail:{batch_id}")
        if cached:
            return cached

        batch = await self.repo.get_with_products(batch_id)
        if not batch:
            raise NotFoundError(f"Batch {batch_id} not found")
        return batch

    async def update_batch(self, batch_id: int, data: BatchUpdate) -> Batch:
        batch = await self.repo.get_by_id(batch_id)
        if not batch:
            raise NotFoundError(f"Batch {batch_id} not found")

        update_data = data.model_dump(exclude_unset=True)

        if "is_closed" in update_data:
            if update_data["is_closed"] and not batch.is_closed:
                update_data["closed_at"] = datetime.utcnow()
            elif not update_data["is_closed"] and batch.is_closed:
                update_data["closed_at"] = None

        batch = await self.repo.update(batch, **update_data)
        await self._invalidate_batch_cache(batch_id)
        return batch

    async def list_batches(
        self,
        is_closed: bool | None = None,
        batch_number: int | None = None,
        batch_date: date | None = None,
        work_center_id: int | None = None,
        shift: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Batch], int]:
        return await self.repo.get_filtered(
            is_closed=is_closed,
            batch_number=batch_number,
            batch_date=batch_date,
            work_center_id=work_center_id,
            shift=shift,
            offset=offset,
            limit=limit,
        )

    async def _invalidate_list_cache(self):
        await self.cache.delete("dashboard_stats")
        await self.cache.delete_pattern("batches_list:*")

    async def _invalidate_batch_cache(self, batch_id: int):
        await self.cache.delete(f"batch_detail:{batch_id}")
        await self.cache.delete(f"batch_statistics:{batch_id}")
        await self.cache.delete("dashboard_stats")
        await self.cache.delete_pattern("batches_list:*")
