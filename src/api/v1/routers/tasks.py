from fastapi import APIRouter

from src.celery_app import celery_app
from src.api.v1.schemas.task import TaskStatusResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    result = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": result.status,
        "result": None,
    }

    if result.status == "PROGRESS":
        response["result"] = result.info
    elif result.status == "SUCCESS":
        response["result"] = result.result
    elif result.status == "FAILURE":
        response["result"] = {"error": str(result.result)}

    return TaskStatusResponse(**response)
