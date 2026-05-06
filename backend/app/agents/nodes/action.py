import uuid

from langgraph.types import RunnableConfig, interrupt

from app.agents.llm import LLMClient, call_action_llm
from app.agents.state import InvestigationState
from app.db.models import HILInboxItem
from app.services.idempotency import compute_key


async def action_node(state: InvestigationState, config: RunnableConfig) -> dict:
    client: LLMClient = config["configurable"]["llm_client"]
    session_factory = config["configurable"]["session_factory"]

    result = await call_action_llm(state, client)
    action = result.action
    updates: dict = {"proposed_action": action}

    if action in ("retrain", "rollback"):
        key = compute_key(state["investigation_id"], action, state["model_uri_at_open"])
        updates["idempotency_key"] = key

        async with session_factory() as session:
            hil_item = HILInboxItem(
                investigation_id=uuid.UUID(state["investigation_id"]),
                proposed_action=action,
                idempotency_key=key,
                status="pending",
            )
            session.add(hil_item)
            await session.commit()

        interrupt({"proposed_action": action, "idempotency_key": key})

    return updates
