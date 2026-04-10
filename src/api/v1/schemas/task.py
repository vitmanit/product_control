from typing import Any
from pydantic import BaseModel


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # PENDING, PROGRESS, SUCCESS, FAILURE
    result: Any | None = None
