from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Investigation
from app.db.session import get_session
from app.schemas.investigations import DriftWebhookPayload

router = APIRouter(prefix="/v1/webhooks")


@router.post("/drift", status_code=202)
async def receive_drift_webhook(
    payload: DriftWebhookPayload,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    investigation = Investigation(
        event_id=payload.event_id,
        model_name=payload.model_name,
        model_version=payload.model_version,
        model_uri_at_open=payload.model_uri,
        severity=payload.severity,
        previous_severity=payload.previous_severity,
        status="open",
    )
    session.add(investigation)
    await session.commit()

    # TODO: kick off LangGraph agent in background (Step 5)

    return {"status": "accepted", "investigation_id": str(investigation.id)}
