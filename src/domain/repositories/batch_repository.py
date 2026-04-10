from datetime import date, datetime
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.domain.models.batch import Batch
from src.domain.repositories.base_repository import BaseRepository


class BatchRepository(BaseRepository[Batch]):
    def __init__(self, session: AsyncSession):
        super().__init__(Batch, session)

    async def get_with_products(self, batch_id: int) -> Batch | None:
        query = (
            select(Batch)
            .options(joinedload(Batch.products), joinedload(Batch.work_center))
            .where(Batch.id == batch_id)
        )
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_filtered(
        self,
        is_closed: bool | None = None,
        batch_number: int | None = None,
        batch_date: date | None = None,
        work_center_id: int | None = None,
        shift: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Batch], int]:
        base = select(Batch)
        count_base = select(func.count()).select_from(Batch)

        conditions = []
        if is_closed is not None:
            conditions.append(Batch.is_closed == is_closed)
        if batch_number is not None:
            conditions.append(Batch.batch_number == batch_number)
        if batch_date is not None:
            conditions.append(Batch.batch_date == batch_date)
        if work_center_id is not None:
            conditions.append(Batch.work_center_id == work_center_id)
        if shift is not None:
            conditions.append(Batch.shift == shift)

        if conditions:
            base = base.where(*conditions)
            count_base = count_base.where(*conditions)

        total = (await self.session.execute(count_base)).scalar()

        query = (
            base
            .options(joinedload(Batch.work_center))
            .order_by(Batch.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        items = result.unique().scalars().all()

        return items, total

    async def get_expired_batches(self) -> Sequence[Batch]:
        query = select(Batch).where(
            Batch.is_closed == False,
            Batch.shift_end < func.now(),
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_number_and_date(self, batch_number: int, batch_date: date) -> Batch | None:
        query = select(Batch).where(
            Batch.batch_number == batch_number,
            Batch.batch_date == batch_date,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
