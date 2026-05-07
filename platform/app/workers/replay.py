import joblib
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ActionJob, Prediction
from app.ml.predict import engineer_features
from app.schemas.predict import PredictionRequest

logger = structlog.get_logger()

async def handle_replay(job: ActionJob, session: AsyncSession) -> dict:
    pipeline = joblib.load(settings.model_artifact_path)

    stmt = (
        select(Prediction)
        .where(Prediction.model_name == settings.model_name)
        .order_by(Prediction.created_at.desc())
        .limit(settings.replay_window_size)
    )
    predictions = list((await session.execute(stmt)).scalars().all())

    if not predictions:
        return {"replayed": 0, "matched": 0, "mismatched": 0, "message": "no predictions to replay"}

    matched, mismatched, mismatches = 0, 0, []
    for p in predictions:
        req = PredictionRequest.model_validate(p.request_payload)
        X = engineer_features(req)
        new_proba = float(pipeline.predict_proba(X)[0, 1])
        if abs(new_proba - p.probability) < 1e-12:
            matched += 1
        else:
            mismatched += 1
            if len(mismatches) < 5:
                mismatches.append({"id": str(p.id), "old": p.probability, "new": new_proba})

    logger.info("replay.complete", job_id=str(job.id), replayed=len(predictions), mismatched=mismatched)
    return {
        "replayed": len(predictions),
        "matched": matched,
        "mismatched": mismatched,
        "fidelity_passed": mismatched == 0,
        "sample_mismatches": mismatches,
    }
