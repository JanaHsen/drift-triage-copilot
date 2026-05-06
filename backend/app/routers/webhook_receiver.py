import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import InvestigationState
from app.db.models import Investigation
from app.db.session import get_session
from app.schemas.investigations import DriftWebhookPayload

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
    if final_state and not final_state.get("is_stale"):
        async with session_factory() as session:
            investigation = await session.get(Investigation, uuid.UUID(investigation_id))
            if investigation:
                investigation.action_decided = final_state.get("proposed_action")
                investigation.summary = final_state.get("summary")
                investigation.resolution = final_state.get("resolution")
                investigation.status = "resolved"
                await session.commit()


@router.post("/drift", status_code=202)
async def receive_drift_webhook(
    payload: DriftWebhookPayload,
    request: Request,
    background_tasks: BackgroundTasks,
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
        "is_stale": False,
        "dispatched": False,
        "summary": None,
        "resolution": None,
        "next": "",
    }

    background_tasks.add_task(
        _run_graph,
        request.app.state.graph,
        initial_state,
        str(investigation.id),
        request.app.state.llm_client,
        request.app.state.session_factory,
    )

    return {"status": "accepted", "investigation_id": str(investigation.id)}
