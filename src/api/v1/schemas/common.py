from typing import TypeVar, Generic
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int


class MessageResponse(BaseModel):
    message: str


class TaskAcceptedResponse(BaseModel):
    task_id: str
    status: str = "PENDING"
    message: str | None = None
