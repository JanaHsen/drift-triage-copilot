import uuid
from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import InvestigationState
from app.core.auth import require_bearer_token
from app.core.dependencies import (
    get_graph,
    get_llm_client,
    get_session,
    get_session_factory,
)
from app.db.models import Investigation
from app.schemas.investigations import DriftWebhookPayload

logger = structlog.get_logger()
router = APIRouter(prefix="/v1/webhooks")


async def _run_graph(
    graph,
    state: InvestigationState,
    investigation_id: str,
    llm_client: object,
    session_factory: object,
) -> None:
    config = {
        "configurable": {
            "thread_id": investigation_id,
            "llm_client": llm_client,
            "session_factory": session_factory,
        }
    }
    final_state = await graph.ainvoke(state, config=config)
    if not final_state:
        return
    async with session_factory() as session:
        investigation = await session.get(Investigation, uuid.UUID(investigation_id))
        if not investigation:
            return
        if final_state.get("is_stale"):
            investigation.is_stale = True
            investigation.status = "resolved"
        elif final_state.get("summary"):
            investigation.action_decided = final_state.get("proposed_action")
            investigation.summary = final_state.get("summary")
            investigation.resolution = final_state.get("resolution")
            investigation.status = "resolved"
        await session.commit()


@router.post("/drift", status_code=202, dependencies=[Depends(require_bearer_token)])
async def receive_drift_webhook(
    payload: DriftWebhookPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    graph: Any = Depends(get_graph),
    llm_client: Any = Depends(get_llm_client),
    session_factory: Any = Depends(get_session_factory),
) -> dict[str, str]:
    logger.info(
        "webhook.received",
        event_id=payload.event_id,
        model_name=payload.model_name,
        severity=payload.severity,
    )
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
    try:
        await session.commit()
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail=f"Event '{payload.event_id}' has already been processed",
        )

    initial_state: InvestigationState = {
        "investigation_id": str(investigation.id),
        "event_id": payload.event_id,
        "model_name": payload.model_name,
        "model_version": payload.model_version,
        "model_uri_at_open": payload.model_uri,
        "severity": payload.severity,
        "previous_severity": payload.previous_severity,
        "drift_summary": payload.drift_summary.model_dump(),
        "triage_result": None,
        "proposed_action": None,
        "idempotency_key": None,
        "approver_user_id": None,
        "is_stale": False,
        "dispatched": False,
        "summary": None,
        "resolution": None,
        "next": "",
    }

    background_tasks.add_task(
        _run_graph,
        graph,
        initial_state,
        str(investigation.id),
        llm_client,
        session_factory,
    )

    return {"status": "accepted", "investigation_id": str(investigation.id)}
