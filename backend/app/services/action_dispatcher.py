import httpx

from app.core.config import settings


async def dispatch_action(
    action_type: str,
    investigation_id: str,
    target_model_uri: str,
    idempotency_key: str,
    approver_user_id: str | None = None,
    payload: dict | None = None,
) -> dict:
    """POST an action request to the platform's action endpoint."""
    body = {
        "schema_version": "1.0",
        "investigation_id": investigation_id,
        "action": action_type,
        "target_model_uri": target_model_uri,
        "approver_user_id": approver_user_id,
        "payload": payload or {},
    }
    headers = {
        "Authorization": f"Bearer {settings.agent_token}",
        "X-Idempotency-Key": idempotency_key,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.platform_base_url}/v1/actions",
            json=body,
            headers=headers,
        )
        resp.raise_for_status()
        return dict(resp.json())
