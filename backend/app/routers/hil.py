import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HILInboxItem, Investigation
from app.db.session import get_session
from app.schemas.hil import HILApproveRequest, HILRejectRequest

router = APIRouter(prefix="/v1/hil")


async def _resume_graph(
    graph,
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
    final_state = await graph.ainvoke(Command(resume={"approved": True}), config=config)
    if final_state and not final_state.get("is_stale"):
        async with session_factory() as session:
            investigation = await session.get(Investigation, uuid.UUID(investigation_id))
            if investigation:
                investigation.summary = final_state.get("summary")
                investigation.resolution = final_state.get("resolution")
                investigation.status = "resolved"
                await session.commit()


@router.post("/{item_id}/approve", status_code=200)
async def approve_hil_item(
    item_id: uuid.UUID,
    body: HILApproveRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict:
    item = await session.get(HILInboxItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="HIL item not found")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail=f"HIL item is already {item.status}")

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
        request.app.state.graph,
        str(investigation.id),
        request.app.state.llm_client,
        request.app.state.session_factory,
    )

    return {"status": "approved", "investigation_id": str(investigation.id)}


@router.post("/{item_id}/reject", status_code=200)
async def reject_hil_item(
    item_id: uuid.UUID,
    body: HILRejectRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    item = await session.get(HILInboxItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="HIL item not found")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail=f"HIL item is already {item.status}")

    item.status = "rejected"
    item.approver_user_id = body.approver_user_id
    item.resolved_at = datetime.now(timezone.utc)

    investigation = await session.get(Investigation, item.investigation_id)
    if investigation:
        investigation.status = "resolved"

    await session.commit()

    return {"status": "rejected", "investigation_id": str(item.investigation_id)}
