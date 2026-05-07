import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from langgraph.types import Command
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_bearer_token
from app.core.dependencies import (
    get_graph,
    get_llm_client,
    get_session,
    get_session_factory,
)
from app.db.models import HILInboxItem, Investigation
from app.schemas.hil import HILApproveRequest, HILRejectRequest

router = APIRouter(prefix="/v1/hil")


class HILItemOut(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    proposed_action: str
    idempotency_key: str
    status: str
    approver_user_id: str | None
    created_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[HILItemOut])
async def list_hil_items(
    status: str | None = "pending",
    session: AsyncSession = Depends(get_session),
) -> list[HILInboxItem]:
    stmt = select(HILInboxItem).order_by(HILInboxItem.created_at.desc())
    if status is not None:
        stmt = stmt.where(HILInboxItem.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _resume_graph(
    graph,
    investigation_id: str,
    approver_user_id: str,
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
    final_state = await graph.ainvoke(
        Command(resume={"approved": True, "approver_user_id": approver_user_id}),
        config=config,
    )
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


@router.post(
    "/{item_id}/approve", status_code=200, dependencies=[Depends(require_bearer_token)]
)
async def approve_hil_item(
    item_id: uuid.UUID,
    body: HILApproveRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    graph: Any = Depends(get_graph),
    llm_client: Any = Depends(get_llm_client),
    session_factory: Any = Depends(get_session_factory),
) -> dict:
    item = await session.get(HILInboxItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="HIL item not found")
    if item.status != "pending":
        raise HTTPException(
            status_code=409, detail=f"HIL item is already {item.status}"
        )

    investigation = await session.get(Investigation, item.investigation_id)
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if investigation.is_stale:
        raise HTTPException(
            status_code=409,
            detail="Investigation is stale — model URI changed since recommendation was made",
        )

    item.status = "approved"
    item.approver_user_id = body.approver_user_id
    item.resolved_at = datetime.now(timezone.utc)
    await session.commit()

    background_tasks.add_task(
        _resume_graph,
        graph,
        str(investigation.id),
        body.approver_user_id,
        llm_client,
        session_factory,
    )

    return {"status": "approved", "investigation_id": str(investigation.id)}


@router.post(
    "/{item_id}/reject", status_code=200, dependencies=[Depends(require_bearer_token)]
)
async def reject_hil_item(
    item_id: uuid.UUID,
    body: HILRejectRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    item = await session.get(HILInboxItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="HIL item not found")
    if item.status != "pending":
        raise HTTPException(
            status_code=409, detail=f"HIL item is already {item.status}"
        )

    item.status = "rejected"
    item.approver_user_id = body.approver_user_id
    item.resolved_at = datetime.now(timezone.utc)

    investigation = await session.get(Investigation, item.investigation_id)
    if investigation:
        investigation.status = "resolved"

    await session.commit()

    return {"status": "rejected", "investigation_id": str(item.investigation_id)}
