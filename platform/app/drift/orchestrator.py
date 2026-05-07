import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import DriftSnapshot, Prediction
from app.drift.detector import compute_drift
from app.drift.emitter import emit_drift_webhook
from app.drift.severity import classify_severity
from app.ml.loader import LoadedModel

logger = structlog.get_logger()


async def run_drift_check(
    session: AsyncSession,
    http_client,
    loaded_model: LoadedModel,
) -> DriftSnapshot:
    stmt = (
        select(Prediction)
        .where(Prediction.model_name == loaded_model.model_name)
        .order_by(Prediction.created_at.desc())
        .limit(settings.drift_window_size)
    )
    predictions = list((await session.execute(stmt)).scalars().all())

    if not predictions:
        raise ValueError("No predictions in window; cannot compute drift")

    payloads = [p.request_payload for p in predictions]
    probas = [p.probability for p in predictions]
    window_start = min(p.created_at for p in predictions)
    window_end = max(p.created_at for p in predictions)

    drift = compute_drift(payloads, probas, loaded_model.reference_stats)

    severity = classify_severity(
        drift["psi_features"],
        drift["output_distribution_drift"],
        threshold_medium=settings.drift_psi_threshold_medium,
        threshold_high=settings.drift_psi_threshold_high,
        threshold_critical=settings.drift_psi_threshold_critical,
    )

    prev_stmt = (
        select(DriftSnapshot)
        .where(DriftSnapshot.model_name == loaded_model.model_name)
        .order_by(DriftSnapshot.created_at.desc())
        .limit(1)
    )
    previous = (await session.execute(prev_stmt)).scalar_one_or_none()
    previous_severity = previous.severity if previous else None

    snapshot = DriftSnapshot(
        model_name=loaded_model.model_name,
        model_version=loaded_model.model_version,
        severity=severity,
        previous_severity=previous_severity,
        n_predictions=len(predictions),
        window_start=window_start,
        window_end=window_end,
        psi_features=drift["psi_features"],
        chi2_features=drift["chi2_features"],
        output_distribution_drift=drift["output_distribution_drift"],
        webhook_emitted=False,
    )

    # Suppress the "first run, still low" case — not a meaningful transition.
    should_emit = (
        previous_severity != severity
        and not (previous_severity is None and severity == "low")
    )

    if should_emit:
        try:
            event_id = await emit_drift_webhook(
                http_client,
                model_name=loaded_model.model_name,
                model_version=loaded_model.model_version,
                model_uri=f"models:/{loaded_model.model_name}/{loaded_model.model_version}",
                severity=severity,
                previous_severity=previous_severity,
                psi_features=drift["psi_features"],
                chi2_features=drift["chi2_features"],
                output_distribution_drift=drift["output_distribution_drift"],
                window_start=window_start,
                window_end=window_end,
                n_predictions=len(predictions),
            )
            snapshot.webhook_emitted = True
            snapshot.webhook_event_id = event_id
        except Exception as exc:
            # Persist the snapshot regardless — operator needs the computed scores
            # even if webhook delivery failed.
            logger.warning("drift.webhook_failed", error=str(exc))

    session.add(snapshot)
    await session.commit()
    await session.refresh(snapshot)
    return snapshot
