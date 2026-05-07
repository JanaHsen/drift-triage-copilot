"""Promotion contract — separate from action dispatch (synchronous, fast, single registry write)."""

from datetime import datetime

from pydantic import BaseModel


class ChecklistResult(BaseModel):
    name: str
    passed: bool
    detail: str | None = None


class PromotionRequest(BaseModel):
    schema_version: str = "1.0"
    model_name: str
    target_version: str
    approver_user_id: str
    investigation_id: str | None = None  # optional — promote can be called without an agent investigation
    request_id: str  # idempotency key for this promotion attempt
    reason: str | None = None


class PromotionResponse(BaseModel):
    promoted: bool
    model_name: str
    promoted_version: str | None
    archived_versions: list[str]
    checklist: list[ChecklistResult]
    audit_log_id: str
    message: str
    timestamp: datetime
