from datetime import datetime
from pydantic import BaseModel


class ProductCreate(BaseModel):
    unique_code: str
    batch_id: int


class ProductResponse(BaseModel):
    id: int
    unique_code: str
    batch_id: int
    is_aggregated: bool
    aggregated_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AggregateRequest(BaseModel):
    unique_codes: list[str]


class AggregateResult(BaseModel):
    success: bool = True
    total: int
    aggregated: int
    failed: int
    errors: list[dict] = []
