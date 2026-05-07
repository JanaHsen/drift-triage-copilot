from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel
from rq.job import Job

from app.queue.client import dlq, queue, redis_conn

router = APIRouter(prefix="/v1/queue")


class QueueJob(BaseModel):
    job_id: str
    action: str
    investigation_id: str
    model_uri: str
    approver_user_id: str | None
    enqueued_at: datetime | None


class QueueStats(BaseModel):
    queue_depth: int
    dlq_depth: int
    jobs: list[QueueJob]
    dlq_jobs: list[QueueJob]


def _to_queue_job(job: Job) -> QueueJob:
    payload: dict = job.args[0] if job.args else {}
    return QueueJob(
        job_id=job.id,
        action=payload.get("action", "unknown"),
        investigation_id=payload.get("investigation_id", ""),
        model_uri=payload.get("model_uri", ""),
        approver_user_id=payload.get("approver_user_id"),
        enqueued_at=job.enqueued_at,
    )


@router.get("/stats", response_model=QueueStats)
async def queue_stats() -> QueueStats:
    job_ids = queue.job_ids
    dlq_job_ids = dlq.job_ids

    jobs = [
        _to_queue_job(j)
        for j in Job.fetch_many(job_ids, connection=redis_conn)
        if j is not None
    ]
    dlq_jobs = [
        _to_queue_job(j)
        for j in Job.fetch_many(dlq_job_ids, connection=redis_conn)
        if j is not None
    ]

    return QueueStats(
        queue_depth=len(job_ids),
        dlq_depth=len(dlq_job_ids),
        jobs=jobs,
        dlq_jobs=dlq_jobs,
    )
