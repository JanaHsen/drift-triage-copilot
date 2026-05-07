"""POST /drift/check — manual trigger for drift computation + webhook emission."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_bearer_token
from app.db.session import get_session
from app.drift.service import run_drift_check

router = APIRouter(tags=["drift"])


class DriftCheckResponse(BaseModel):
    snapshot_id: str
    severity: str
    previous_severity: str | None
    n_predictions: int
    webhook_emitted: bool
    webhook_event_id: str | None


@router.post(
    "/drift/check",
    response_model=DriftCheckResponse,
    dependencies=[Depends(require_bearer_token)],
)
async def trigger_drift_check(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> DriftCheckResponse:
    try:
        snapshot = await run_drift_check(
            session=session,
            http_client=request.app.state.http_client,
            loaded_model=request.app.state.loaded_model,
        )
    except ValueError as exc:
        # Empty window — caller needs to send some predictions first.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return DriftCheckResponse(
        snapshot_id=str(snapshot.id),
        severity=snapshot.severity,
        previous_severity=snapshot.previous_severity,
        n_predictions=snapshot.n_predictions,
        webhook_emitted=snapshot.webhook_emitted,
        webhook_event_id=snapshot.webhook_event_id,
    )
