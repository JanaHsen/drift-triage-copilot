"""HTTP client that POSTs DriftWebhookPayload to the agent's receiver."""

import logging
import uuid
from datetime import datetime, timezone

import httpx

from app.core.settings import settings
from contracts.v1.webhooks import DriftSummary, DriftWebhookPayload, DriftWindow

logger = logging.getLogger(__name__)


async def emit_drift_webhook(
    http_client: httpx.AsyncClient,
    *,
    model_name: str,
    model_version: str,
    model_uri: str,
    severity: str,
    previous_severity: str | None,
    psi_features: dict[str, float],
    chi2_features: dict[str, float],
    output_distribution_drift: float,
    window_start: datetime,
    window_end: datetime,
    n_predictions: int,
) -> str:
    """POST DriftWebhookPayload to agent. Returns event_id. Re-raises on failure."""
    event_id = str(uuid.uuid4())
    payload = DriftWebhookPayload(
        event_id=event_id,
        timestamp=datetime.now(timezone.utc),
        model_name=model_name,
        model_version=model_version,
        model_uri=model_uri,
        severity=severity,
        previous_severity=previous_severity,
        drift_summary=DriftSummary(
            psi_features=psi_features,
            chi2_features=chi2_features,
            output_distribution_drift=output_distribution_drift,
        ),
        window=DriftWindow(start=window_start, end=window_end, n_predictions=n_predictions),
    )

    url = f"{settings.agent_base_url}/v1/webhooks/drift"
    headers = {"Authorization": f"Bearer {settings.agent_token}"}

    response = await http_client.post(
        url,
        json=payload.model_dump(mode="json"),
        headers=headers,
        timeout=10.0,
    )
    response.raise_for_status()

    logger.info(
        "Emitted drift webhook event_id=%s severity=%s prev=%s -> %s",
        event_id, severity, previous_severity, url,
    )
    return event_id
