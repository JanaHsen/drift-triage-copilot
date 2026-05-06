import httpx

from app.core.config import settings
from app.queue.client import redis_conn
from app.schemas.jobs import JobPayload

_EXEC_TTL = 3600  # 1h — guards against RQ retries running the action twice


def run_replay(payload_dict: dict) -> None:
    payload = JobPayload(**payload_dict)

    exec_key = f"exec:{payload.idempotency_key}"
    if not redis_conn.set(exec_key, "1", nx=True, ex=_EXEC_TTL):
        return

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{settings.platform_base_url}/v1/actions/replay",
            json={
                "schema_version": "1.0",
                "investigation_id": payload.investigation_id,
                "action": "replay",
                "target_model_uri": payload.model_uri,
                "payload": {},
            },
            headers={
                "Authorization": f"Bearer {settings.agent_token}",
                "X-Idempotency-Key": payload.idempotency_key,
            },
        )
        response.raise_for_status()
