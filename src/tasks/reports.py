import asyncio
import os
from datetime import datetime

from src.celery_app import celery_app
from src.core.database import AsyncSessionLocal
from src.core.config import settings
from src.domain.repositories.batch_repository import BatchRepository
from src.domain.repositories.product_repository import ProductRepository
from src.storage.minio_service import minio_service
from src.utils.excel_generator import generate_batch_report_excel
from src.utils.pdf_generator import generate_batch_report_pdf


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _generate_report(batch_id: int, format: str) -> dict:
    async with AsyncSessionLocal() as session:
        batch_repo = BatchRepository(session)
        product_repo = ProductRepository(session)

        batch = await batch_repo.get_with_products(batch_id)
        if not batch:
            return {"success": False, "error": f"Batch {batch_id} not found"}

        stats = await product_repo.count_by_batch(batch_id)

        batch_data = {
            "batch_number": batch.batch_number,
            "batch_date": str(batch.batch_date),
            "is_closed": batch.is_closed,
            "work_center_name": batch.work_center.name if batch.work_center else "",
            "shift": batch.shift,
            "team": batch.team,
            "nomenclature": batch.nomenclature,
            "ekn_code": batch.ekn_code,
            "shift_start": str(batch.shift_start),
            "shift_end": str(batch.shift_end),
        }

        products = [
            {
                "id": p.id,
                "unique_code": p.unique_code,
                "is_aggregated": p.is_aggregated,
                "aggregated_at": str(p.aggregated_at) if p.aggregated_at else None,
            }
            for p in batch.products
        ]

    if format == "pdf":
        file_path = generate_batch_report_pdf(batch_data, products, stats)
        ext = "pdf"
    else:
        file_path = generate_batch_report_excel(batch_data, products, stats)
        ext = "xlsx"

    object_name = f"batch_{batch_id}_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}"
    file_url = minio_service.upload_file(
        bucket=settings.minio_bucket_reports,
        file_path=file_path,
        object_name=object_name,
    )

    file_size = os.path.getsize(file_path)
    os.unlink(file_path)

    return {
        "success": True,
        "file_url": file_url,
        "file_name": object_name,
        "file_size": file_size,
    }


@celery_app.task(bind=True, max_retries=3, name="src.tasks.reports.generate_batch_report")
def generate_batch_report(self, batch_id: int, format: str = "excel", user_email: str | None = None):
    return _run_async(_generate_report(batch_id, format))
