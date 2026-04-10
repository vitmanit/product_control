from datetime import date

from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db, get_cache
from src.core.cache import RedisCache
from src.core.config import settings
from src.domain.services.batch_service import BatchService
from src.domain.services.webhook_service import WebhookService
from src.api.v1.schemas.batch import (
    BatchCreateItem, BatchUpdate, BatchResponse, BatchListItem,
    ReportRequest, ExportRequest,
)
from src.api.v1.schemas.common import PaginatedResponse, TaskAcceptedResponse
from src.api.v1.schemas.product import AggregateRequest
from src.tasks.aggregation import aggregate_products_batch
from src.tasks.reports import generate_batch_report
from src.tasks.imports import import_batches_from_file
from src.tasks.exports import export_batches_to_file
from src.storage.minio_service import minio_service

import tempfile
import os

router = APIRouter(prefix="/batches", tags=["batches"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=list[BatchResponse])
async def create_batches(
    items: list[BatchCreateItem],
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
):
    service = BatchService(db, cache)
    batches = await service.create_batches(items)

    # Trigger webhooks
    webhook_service = WebhookService(db)
    for batch in batches:
        delivery_ids = await webhook_service.trigger_event("batch_created", {
            "id": batch.id,
            "batch_number": batch.batch_number,
            "batch_date": str(batch.batch_date),
            "nomenclature": batch.nomenclature,
        })
        from src.tasks.webhooks import send_webhook_delivery
        for did in delivery_ids:
            send_webhook_delivery.delay(did)

    return batches


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
):
    service = BatchService(db, cache)
    return await service.get_batch(batch_id)


@router.patch("/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: int,
    data: BatchUpdate,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
):
    service = BatchService(db, cache)
    batch = await service.update_batch(batch_id, data)

    # Webhook events
    webhook_service = WebhookService(db)
    event_type = "batch_closed" if batch.is_closed else "batch_updated"
    event_data = {"id": batch.id, "batch_number": batch.batch_number}
    if batch.is_closed:
        event_data["closed_at"] = str(batch.closed_at)

    delivery_ids = await webhook_service.trigger_event(event_type, event_data)
    from src.tasks.webhooks import send_webhook_delivery
    for did in delivery_ids:
        send_webhook_delivery.delay(did)

    return batch


@router.get("", response_model=PaginatedResponse[BatchListItem])
async def list_batches(
    is_closed: bool | None = None,
    batch_number: int | None = None,
    batch_date: date | None = None,
    work_center_id: int | None = None,
    shift: str | None = None,
    offset: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
):
    service = BatchService(db, cache)
    items, total = await service.list_batches(
        is_closed=is_closed,
        batch_number=batch_number,
        batch_date=batch_date,
        work_center_id=work_center_id,
        shift=shift,
        offset=offset,
        limit=min(limit, 100),
    )
    return PaginatedResponse(items=items, total=total, offset=offset, limit=limit)


@router.post(
    "/{batch_id}/aggregate-async",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskAcceptedResponse,
)
async def aggregate_async(
    batch_id: int,
    data: AggregateRequest,
    db: AsyncSession = Depends(get_db),
):
    task = aggregate_products_batch.delay(batch_id, data.unique_codes)
    return TaskAcceptedResponse(
        task_id=task.id,
        status="PENDING",
        message="Aggregation task started",
    )


@router.post(
    "/{batch_id}/reports",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskAcceptedResponse,
)
async def create_report(
    batch_id: int,
    data: ReportRequest,
):
    task = generate_batch_report.delay(batch_id, data.format, data.email)
    return TaskAcceptedResponse(
        task_id=task.id,
        status="PENDING",
        message="Report generation started",
    )


@router.post(
    "/import",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskAcceptedResponse,
)
async def import_batches(file: UploadFile = File(...)):
    # Сохраняем файл в MinIO
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1])
    content = await file.read()
    tmp.write(content)
    tmp.close()

    object_name = f"import_{file.filename}"
    minio_service.upload_file(
        bucket=settings.minio_bucket_imports,
        file_path=tmp.name,
        object_name=object_name,
    )
    os.unlink(tmp.name)

    task = import_batches_from_file.delay("", object_name)
    return TaskAcceptedResponse(
        task_id=task.id,
        status="PENDING",
        message="File uploaded, import started",
    )


@router.post(
    "/export",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskAcceptedResponse,
)
async def export_batches(data: ExportRequest):
    task = export_batches_to_file.delay(data.filters or {}, data.format)
    return TaskAcceptedResponse(
        task_id=task.id,
        status="PENDING",
        message="Export started",
    )
