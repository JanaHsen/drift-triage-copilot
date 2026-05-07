import pytest
from pydantic import ValidationError

from app.schemas.investigations import DriftWebhookPayload
from app.schemas.jobs import JobPayload

_VALID_DRIFT_PAYLOAD = {
    "event_id": "evt-001",
    "timestamp": "2024-01-01T00:00:00Z",
    "model_name": "bank-churn",
    "model_version": "v3",
    "model_uri": "models:/bank-churn/3",
    "severity": "high",
    "previous_severity": "medium",
    "drift_summary": {
        "psi_features": {"age": 0.18},
        "chi2_features": {"job": 0.05},
        "output_distribution_drift": 0.1,
    },
    "window": {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-01T01:00:00Z",
        "n_predictions": 100,
    },
}


def test_drift_webhook_payload_valid():
    payload = DriftWebhookPayload(**_VALID_DRIFT_PAYLOAD)
    assert payload.severity == "high"
    assert payload.previous_severity == "medium"
    assert payload.schema_version == "1.0"


def test_drift_webhook_payload_no_previous_severity():
    data = {**_VALID_DRIFT_PAYLOAD, "severity": "low"}
    del data["previous_severity"]
    payload = DriftWebhookPayload(**data)
    assert payload.previous_severity is None


def test_drift_webhook_payload_invalid_severity():
    with pytest.raises(ValidationError):
        DriftWebhookPayload(**{**_VALID_DRIFT_PAYLOAD, "severity": "extreme"})


def test_drift_webhook_payload_missing_required_field():
    data = {**_VALID_DRIFT_PAYLOAD}
    del data["event_id"]
    with pytest.raises(ValidationError):
        DriftWebhookPayload(**data)


def test_job_payload_valid():
    payload = JobPayload(
        investigation_id="inv-001",
        action="replay",
        model_uri="models:/bank-churn/3",
        idempotency_key="abc123",
    )
    assert payload.action == "replay"
    assert payload.approver_user_id is None


def test_job_payload_with_approver():
    payload = JobPayload(
        investigation_id="inv-001",
        action="retrain",
        model_uri="models:/bank-churn/3",
        idempotency_key="abc123",
        approver_user_id="user-42",
    )
    assert payload.approver_user_id == "user-42"


def test_job_payload_missing_required_field():
    with pytest.raises(ValidationError):
        JobPayload(
            investigation_id="inv-001",
            action="replay",
            model_uri="models:/bank-churn/3",
        )
