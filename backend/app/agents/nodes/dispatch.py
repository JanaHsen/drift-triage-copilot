import structlog

from app.agents.state import InvestigationState
from app.queue.enqueue import enqueue_job
from app.schemas.jobs import JobPayload


def dispatch_node(state: InvestigationState) -> dict:
    logger = structlog.get_logger().bind(investigation_id=state["investigation_id"])
    action = state.get("proposed_action")
    if action in ("replay", "retrain", "rollback"):
        payload = JobPayload(
            investigation_id=state["investigation_id"],
            action=action,
            model_uri=state["model_uri_at_open"],
            idempotency_key=state["idempotency_key"],
            approver_user_id=state.get("approver_user_id"),
        )
        enqueued = enqueue_job(payload)
        logger.info("dispatch.enqueued", action=action, enqueued=enqueued)
    else:
        logger.info("dispatch.skipped", action=action)
    return {"dispatched": True}
