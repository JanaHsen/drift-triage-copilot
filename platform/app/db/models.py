"""Platform-side ORM tables. Distinct names from backend — no collisions."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Prediction(Base):
    """One row per scored request. Powers the drift detector's rolling window."""

    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String, index=True)
    model_version: Mapped[str] = mapped_column(String, index=True)
    threshold: Mapped[float] = mapped_column(Float)
    probability: Mapped[float] = mapped_column(Float)
    prediction: Mapped[bool] = mapped_column(Boolean)
    request_payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class DriftSnapshot(Base):
    """One row per drift computation. Severity transitions trigger webhooks."""

    __tablename__ = "drift_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String, index=True)
    model_version: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[str] = mapped_column(String, index=True)
    previous_severity: Mapped[str | None] = mapped_column(String, nullable=True)
    n_predictions: Mapped[int] = mapped_column(Integer)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    psi_features: Mapped[dict] = mapped_column(JSON)
    chi2_features: Mapped[dict] = mapped_column(JSON)
    output_distribution_drift: Mapped[float] = mapped_column(Float)
    webhook_emitted: Mapped[bool] = mapped_column(Boolean, default=False)
    webhook_event_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class ActionJob(Base):
    """Audit row for every dispatched action. Status updated by the worker."""

    __tablename__ = "action_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String, index=True)
    target_model_uri: Mapped[str] = mapped_column(String)
    approver_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default="queued", index=True)  # queued | running | succeeded | failed
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PromotionAudit(Base):
    """Every promotion attempt — succeeded or blocked — gets a row."""

    __tablename__ = "promotion_audit"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    model_name: Mapped[str] = mapped_column(String, index=True)
    target_version: Mapped[str] = mapped_column(String)
    approver_user_id: Mapped[str] = mapped_column(String)
    investigation_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    promoted: Mapped[bool] = mapped_column(Boolean)
    archived_versions: Mapped[list] = mapped_column(JSON, default=list)
    checklist_results: Mapped[list] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
