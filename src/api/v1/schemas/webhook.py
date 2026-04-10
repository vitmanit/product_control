from datetime import datetime
from pydantic import BaseModel, Field


class WebhookCreate(BaseModel):
    url: str
    events: list[str]
    secret_key: str
    retry_count: int = 3
    timeout: int = 10


class WebhookUpdate(BaseModel):
    url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None
    retry_count: int | None = None
    timeout: int | None = None


class WebhookResponse(BaseModel):
    id: int
    url: str
    events: list[str]
    is_active: bool
    retry_count: int
    timeout: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebhookDeliveryResponse(BaseModel):
    id: int
    event_type: str
    status: str
    attempts: int
    response_status: int | None = None
    response_body: str | None = None
    error_message: str | None = None
    created_at: datetime
    delivered_at: datetime | None = None

    model_config = {"from_attributes": True}
