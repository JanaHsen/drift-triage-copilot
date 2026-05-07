"""POST /v1/actions — receives ActionRequest from agent, enqueues for worker."""

import hashlib
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_bearer_token
from app.db.models import ActionJob
from app.db.session import get_session
from app.queue.client import claim_idempotency_key, enqueue_job
from contracts.v1.actions import ActionRequest, ActionResponse

router = APIRouter(prefix="/v1/actions", tags=["actions"])


def _derive_idempotency_key(req: ActionRequest) -> str:
    """
    Contract has no idempotency_key field (open issue with Rasha). Derive a
    deterministic one from the request fields that uniquely identify it:
    same investigation + same action + same target = same key. Repeated
    requests with these three identical get deduped in Redis.
    """
    raw = f"{req.investigation_id}|{req.action}|{req.target_model_uri}"
    return hashlib.sha256(raw.encode()).hexdigest()


@router.post(
    "",
    response_model=ActionResponse,
    dependencies=[Depends(require_bearer_token)],
)
async def receive_action(
    payload: ActionRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ActionResponse:
    redis_client = request.app.state.redis_client
    idempotency_key = _derive_idempotency_key(payload)

    # Check if we've seen this exact action before.
    new_job_id = str(uuid.uuid4())
    existing_job_id = await claim_idempotency_key(
        redis_client, idempotency_key, new_job_id
    )

    if existing_job_id is not None:
        # Already claimed. Look up the existing ActionJob row to confirm and
        # return the same job_id — the agent will see the retry succeed
        # without us doing the work twice.
        stmt = select(ActionJob).where(ActionJob.idempotency_key == idempotency_key)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            return ActionResponse(
                accepted=True,
                job_id=str(existing.id),
                message=f"duplicate request; returning original job_id (status={existing.status})",
            )

    # First-time request. Persist the job, then enqueue.
    job = ActionJob(
        id=uuid.UUID(new_job_id),
        investigation_id=payload.investigation_id,
        action=payload.action,
        target_model_uri=payload.target_model_uri,
        approver_user_id=payload.approver_user_id,
        idempotency_key=idempotency_key,
        payload=payload.payload,
        status="queued",
    )
    session.add(job)
    await session.commit()

    await enqueue_job(
        redis_client,
        job_id=new_job_id,
        payload={
            "job_id": new_job_id,
            "investigation_id": payload.investigation_id,
            "action": payload.action,
            "target_model_uri": payload.target_model_uri,
            "approver_user_id": payload.approver_user_id,
            "payload": payload.payload,
        },
    )

    return ActionResponse(
        accepted=True,
        job_id=new_job_id,
        message=f"action '{payload.action}' queued for execution",
    )
