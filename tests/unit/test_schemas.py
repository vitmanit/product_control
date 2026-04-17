from datetime import date, datetime

import pytest
from pydantic import ValidationError

from src.api.v1.schemas.batch import (
    BatchCreateItem,
    BatchUpdate,
    ReportRequest,
    ExportRequest,
)
from src.api.v1.schemas.product import AggregateRequest
from src.api.v1.schemas.webhook import WebhookCreate


def _batch_payload_ru() -> dict:
    return {
        "СтатусЗакрытия": False,
        "ПредставлениеЗаданияНаСмену": "Сменное задание №1",
        "РабочийЦентр": "Линия розлива №1",
        "Смена": "Дневная",
        "Бригада": "Бригада А",
        "НомерПартии": 101,
        "ДатаПартии": "2026-04-17",
        "Номенклатура": "Молоко 2.5% 1л",
        "КодЕКН": "EKN-001",
        "ИдентификаторРЦ": "WC-01",
        "ДатаВремяНачалаСмены": "2026-04-17T08:00:00",
        "ДатаВремяОкончанияСмены": "2026-04-17T20:00:00",
    }


def test_batch_create_accepts_russian_aliases():
    payload = _batch_payload_ru()

    item = BatchCreateItem(**payload)

    assert item.batch_number == 101
    assert item.batch_date == date(2026, 4, 17)
    assert item.work_center_identifier == "WC-01"
    assert item.shift == "Дневная"
    assert item.status_closed is False


def test_batch_create_accepts_english_names():
    item = BatchCreateItem(
        status_closed=True,
        task_description="desc",
        work_center_name="WC",
        shift="A",
        team="T",
        batch_number=1,
        batch_date=date(2026, 4, 17),
        nomenclature="N",
        ekn_code="E",
        work_center_identifier="WC-01",
        shift_start=datetime(2026, 4, 17, 8, 0),
        shift_end=datetime(2026, 4, 17, 20, 0),
    )

    assert item.status_closed is True


def test_batch_create_missing_field_fails():
    payload = _batch_payload_ru()
    del payload["НомерПартии"]

    with pytest.raises(ValidationError):
        BatchCreateItem(**payload)


def test_batch_update_partial():
    update = BatchUpdate(is_closed=True)

    dumped = update.model_dump(exclude_unset=True)

    assert dumped == {"is_closed": True}


def test_report_request_only_allows_excel_or_pdf():
    assert ReportRequest(format="excel").format == "excel"
    assert ReportRequest(format="pdf").format == "pdf"

    with pytest.raises(ValidationError):
        ReportRequest(format="docx")


def test_export_request_only_allows_excel_or_csv():
    assert ExportRequest(format="excel").format == "excel"
    assert ExportRequest(format="csv").format == "csv"

    with pytest.raises(ValidationError):
        ExportRequest(format="pdf")


def test_aggregate_request_accepts_list():
    req = AggregateRequest(unique_codes=["a", "b", "c"])

    assert req.unique_codes == ["a", "b", "c"]


def test_webhook_create_defaults():
    hook = WebhookCreate(
        url="https://example.com/hook",
        events=["batch_created"],
        secret_key="s",
    )

    assert hook.retry_count == 3
    assert hook.timeout == 10
