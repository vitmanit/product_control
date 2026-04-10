import asyncio
import os
import tempfile
from datetime import datetime

import pandas as pd

from src.celery_app import celery_app
from src.core.database import AsyncSessionLocal
from src.core.config import settings
from src.domain.repositories.batch_repository import BatchRepository
from src.storage.minio_service import minio_service


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _export_batches(filters: dict, format: str) -> dict:
    async with AsyncSessionLocal() as session:
        repo = BatchRepository(session)
        batches, total = await repo.get_filtered(
            is_closed=filters.get("is_closed"),
            batch_number=filters.get("batch_number"),
            batch_date=filters.get("batch_date"),
            work_center_id=filters.get("work_center_id"),
            shift=filters.get("shift"),
            offset=0,
            limit=10000,
        )

        data = []
        for b in batches:
            data.append({
                "ID": b.id,
                "НомерПартии": b.batch_number,
                "ДатаПартии": str(b.batch_date),
                "Номенклатура": b.nomenclature,
                "КодЕКН": b.ekn_code,
                "Смена": b.shift,
                "Бригада": b.team,
                "Статус": "Закрыта" if b.is_closed else "Открыта",
                "ОписаниеЗадания": b.task_description,
            })

    df = pd.DataFrame(data)

    ext = "csv" if format == "csv" else "xlsx"
    tmp = tempfile.NamedTemporaryFile(
        suffix=f".{ext}",
        prefix=f"batches_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_",
        delete=False,
    )

    if format == "csv":
        df.to_csv(tmp.name, index=False, encoding="utf-8-sig")
    else:
        df.to_excel(tmp.name, index=False, engine="openpyxl")

    tmp.close()

    object_name = os.path.basename(tmp.name)
    file_url = minio_service.upload_file(
        bucket=settings.minio_bucket_exports,
        file_path=tmp.name,
        object_name=object_name,
    )

    os.unlink(tmp.name)

    return {
        "success": True,
        "file_url": file_url,
        "total_batches": total,
    }


@celery_app.task(name="src.tasks.exports.export_batches_to_file")
def export_batches_to_file(filters: dict, format: str = "excel"):
    return _run_async(_export_batches(filters or {}, format))
