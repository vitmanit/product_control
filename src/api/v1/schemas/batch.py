from datetime import datetime, date
from pydantic import BaseModel, Field


class BatchCreateItem(BaseModel):
    status_closed: bool = Field(alias="СтатусЗакрытия", default=False)
    task_description: str = Field(alias="ПредставлениеЗаданияНаСмену")
    work_center_name: str = Field(alias="РабочийЦентр")
    shift: str = Field(alias="Смена")
    team: str = Field(alias="Бригада")
    batch_number: int = Field(alias="НомерПартии")
    batch_date: date = Field(alias="ДатаПартии")
    nomenclature: str = Field(alias="Номенклатура")
    ekn_code: str = Field(alias="КодЕКН")
    work_center_identifier: str = Field(alias="ИдентификаторРЦ")
    shift_start: datetime = Field(alias="ДатаВремяНачалаСмены")
    shift_end: datetime = Field(alias="ДатаВремяОкончанияСмены")

    model_config = {"populate_by_name": True}


class BatchUpdate(BaseModel):
    is_closed: bool | None = None
    task_description: str | None = None
    shift: str | None = None
    team: str | None = None
    nomenclature: str | None = None
    ekn_code: str | None = None


class ProductInBatch(BaseModel):
    id: int
    unique_code: str
    is_aggregated: bool
    aggregated_at: datetime | None

    model_config = {"from_attributes": True}


class WorkCenterResponse(BaseModel):
    id: int
    identifier: str
    name: str

    model_config = {"from_attributes": True}


class BatchResponse(BaseModel):
    id: int
    is_closed: bool
    closed_at: datetime | None = None
    task_description: str
    work_center_id: int
    shift: str
    team: str
    batch_number: int
    batch_date: date
    nomenclature: str
    ekn_code: str
    shift_start: datetime
    shift_end: datetime
    created_at: datetime
    updated_at: datetime
    products: list[ProductInBatch] = []

    model_config = {"from_attributes": True}


class BatchListItem(BaseModel):
    id: int
    is_closed: bool
    closed_at: datetime | None = None
    task_description: str
    work_center_id: int
    shift: str
    team: str
    batch_number: int
    batch_date: date
    nomenclature: str
    ekn_code: str
    shift_start: datetime
    shift_end: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportRequest(BaseModel):
    format: str = Field(default="excel", pattern="^(excel|pdf)$")
    email: str | None = None


class ImportResponse(BaseModel):
    task_id: str
    status: str = "PENDING"
    message: str = "File uploaded, import started"


class ExportRequest(BaseModel):
    format: str = Field(default="excel", pattern="^(excel|csv)$")
    filters: dict | None = None
