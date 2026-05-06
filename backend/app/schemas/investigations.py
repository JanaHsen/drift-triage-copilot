from datetime import datetime

from pydantic import BaseModel


class DriftSummary(BaseModel):
    psi_features: dict[str, float]
    chi2_features: dict[str, float]
    output_distribution_drift: str


class DriftWindow(BaseModel):
    start: datetime
    end: datetime
    n_predictions: int


class DriftWebhookPayload(BaseModel):
    event_id: str
    timestamp: datetime
    model_name: str
    model_version: str
    model_uri: str
    severity: str
    previous_severity: str | None = None
    drift_summary: DriftSummary
    window: DriftWindow
