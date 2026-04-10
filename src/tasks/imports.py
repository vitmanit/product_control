import asyncio
import os
import tempfile

from src.celery_app import celery_app
from src.core.database import AsyncSessionLocal
from src.core.config import settings
from src.domain.models.batch import Batch
from src.domain.models.work_center import WorkCenter
from src.domain.repositories.batch_repository import BatchRepository
from src.storage.minio_service import minio_service
from src.utils.excel_parser import parse_import_file

from sqlalchemy import select


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _import_batches(file_url: str, object_name: str, task) -> dict:
    # Скачиваем файл из MinIO
    tmp_dir = tempfile.mkdtemp()
    local_path = os.path.join(tmp_dir, object_name)
    minio_service.download_file(settings.minio_bucket_imports, object_name, local_path)

    # Парсим файл
    rows, parse_errors = parse_import_file(local_path)
    os.unlink(local_path)
    os.rmdir(tmp_dir)

    total = len(rows) + len(parse_errors)
    created = 0
    skipped = 0
    errors = list(parse_errors)

    async with AsyncSessionLocal() as session:
        batch_repo = BatchRepository(session)

        for i, row in enumerate(rows):
            # Прогресс
            if (i + 1) % 10 == 0:
                task.update_state(
                    state="PROGRESS",
                    meta={
                        "current": i + 1,
                        "total": len(rows),
                        "created": created,
                        "skipped": skipped,
                    },
                )

            # Проверяем дубликат
            existing = await batch_repo.get_by_number_and_date(
                row["batch_number"], row["batch_date"]
            )
            if existing:
                skipped += 1
                errors.append({
                    "row": i + 2,
                    "error": "Duplicate batch number and date",
                })
                continue

            # Получаем или создаём WorkCenter
            identifier = row.get("work_center_identifier", "")
            name = row.get("work_center_name", identifier)
            if identifier:
                query = select(WorkCenter).where(WorkCenter.identifier == identifier)
                result = await session.execute(query)
                wc = result.scalar_one_or_none()
                if not wc:
                    wc = WorkCenter(identifier=identifier, name=name)
                    session.add(wc)
                    await session.flush()
            else:
                skipped += 1
                errors.append({"row": i + 2, "error": "Missing work center identifier"})
                continue

            batch = Batch(
                is_closed=row.get("status_closed", False),
                task_description=row.get("task_description", ""),
                work_center_id=wc.id,
                shift=row.get("shift", ""),
                team=row.get("team", ""),
                batch_number=row["batch_number"],
                batch_date=row["batch_date"],
                nomenclature=row.get("nomenclature", ""),
                ekn_code=row.get("ekn_code", ""),
                shift_start=row.get("shift_start"),
                shift_end=row.get("shift_end"),
            )
            session.add(batch)
            created += 1

        await session.commit()

    return {
        "success": True,
        "total_rows": total,
        "created": created,
        "skipped": skipped,
        "errors": errors,
    }


@celery_app.task(bind=True, max_retries=1, name="src.tasks.imports.import_batches_from_file")
def import_batches_from_file(self, file_url: str, object_name: str, user_id: int | None = None):
    return _run_async(_import_batches(file_url, object_name, self))
