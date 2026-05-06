from typing import TypedDict


class InvestigationState(TypedDict):
    investigation_id: str
    event_id: str
    model_name: str
    model_version: str
    model_uri_at_open: str
    severity: str
    previous_severity: str | None
    drift_summary: dict
    triage_result: str | None  # "real_drift" | "no_drift"
    proposed_action: str | None  # "no_op" | "replay" | "retrain" | "rollback"
    idempotency_key: str | None
    is_stale: bool
    dispatched: bool
    summary: str | None
    resolution: str | None
    next: str  # routing — set by supervisor on every tick
