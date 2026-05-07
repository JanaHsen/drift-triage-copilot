import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.queue.client import redis_conn
from app.schemas.jobs import JobPayload

EXEC_TTL = 3600  # 1h — guards against RQ retries running the action twice


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500:
        return True
    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception(_is_transient),
    reraise=True,
)
def _post(url: str, json_body: dict, headers: dict) -> None:
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, json=json_body, headers=headers)
        response.raise_for_status()


def run_action(action_type: str, payload_dict: dict, *, require_approver: bool) -> None:
    payload = JobPayload(**payload_dict)

    exec_key = f"exec:{payload.idempotency_key}"
    if not redis_conn.set(exec_key, "1", nx=True, ex=EXEC_TTL):
        return

    body: dict = {
        "schema_version": "1.0",
        "investigation_id": payload.investigation_id,
        "action": action_type,
        "target_model_uri": payload.model_uri,
        "payload": {},
    }
    if require_approver:
        body["approver_user_id"] = payload.approver_user_id

    _post(
        url=f"{settings.platform_base_url}/v1/actions",
        json_body=body,
        headers={
            "Authorization": f"Bearer {settings.agent_token}",
            "X-Idempotency-Key": payload.idempotency_key,
        },
    )
