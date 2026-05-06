from app.queue.client import queue, redis_conn
from app.queue.failure import handle_failure
from app.schemas.jobs import JobPayload

_IDEMPOTENCY_TTL = 86400  # 24h

_ACTION_FUNCS = {
    "replay": "app.agents.actions.replay.run_replay",
    "retrain": "app.agents.actions.retrain.run_retrain",
    "rollback": "app.agents.actions.rollback.run_rollback",
}


def enqueue_job(payload: JobPayload) -> bool:
    key = f"enqueue:{payload.idempotency_key}"
    acquired = redis_conn.set(key, "1", nx=True, ex=_IDEMPOTENCY_TTL)
    if not acquired:
        return False
    func = _ACTION_FUNCS[payload.action]
    queue.enqueue(func, payload.model_dump(), on_failure=handle_failure)
    return True
