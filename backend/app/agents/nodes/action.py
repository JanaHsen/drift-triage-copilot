import uuid

import structlog
from langgraph.types import RunnableConfig, interrupt
from sqlalchemy.exc import IntegrityError

from app.agents.llm import LLMClient, call_action_llm
from app.agents.state import InvestigationState
from app.db.models import HILInboxItem
from app.services.idempotency import compute_key


async def action_node(state: InvestigationState, config: RunnableConfig) -> dict:
    logger = structlog.get_logger().bind(investigation_id=state["investigation_id"])
    client: LLMClient = config["configurable"]["llm_client"]
    session_factory = config["configurable"]["session_factory"]

    logger.info("action.start")
    result = await call_action_llm(state, client)
    action = result.action
    logger.info("action.proposed", action=action)
    updates: dict = {"proposed_action": action}

    if action in ("replay", "retrain", "rollback"):
        key = compute_key(state["investigation_id"], action, state["model_uri_at_open"])
        updates["idempotency_key"] = key

    if action in ("retrain", "rollback"):
        try:
            async with session_factory() as session:
                hil_item = HILInboxItem(
                    investigation_id=uuid.UUID(state["investigation_id"]),
                    proposed_action=action,
                    idempotency_key=updates["idempotency_key"],
                    status="pending",
                )
                session.add(hil_item)
                await session.commit()
        except IntegrityError:
            pass  # node re-ran on resume — HIL item already exists

        logger.info("action.awaiting_hil", action=action)
        resume_data = interrupt(
            {
                "proposed_action": action,
                "idempotency_key": updates["idempotency_key"],
            }
        )
        approver_user_id = (
            resume_data.get("approver_user_id")
            if isinstance(resume_data, dict)
            else None
        )
        logger.info("action.approved", approver_user_id=approver_user_id)
        updates["approver_user_id"] = approver_user_id

    return updates
