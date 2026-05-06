from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SeverityLevel = Literal["low", "medium", "high", "critical"]


class DriftSummary(BaseModel):
    psi_features: dict[str, float]
    chi2_features: dict[str, float]
    output_distribution_drift: float


class DriftWindow(BaseModel):
    start: datetime
    end: datetime
    n_predictions: int


class DriftWebhookPayload(BaseModel):
    schema_version: str = "1.0"
    event_id: str
    timestamp: datetime
    model_name: str
    model_version: str
    model_uri: str
    severity: SeverityLevel
    previous_severity: SeverityLevel | None = None
    drift_summary: DriftSummary
    window: DriftWindow
