"""POST /predict — input validation, scoring, persistence, response."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_bearer_token
from app.db.models import Prediction
from app.core.dependencies import get_session
from app.ml.predict import score
from app.schemas.predict import PredictionRequest, PredictionResponse

router = APIRouter(tags=["predict"])


@router.post(
    "/predict",
    response_model=PredictionResponse,
    # Bearer auth applied as a route-level dependency so the handler signature
    # stays clean. Anything reaching the function body has already passed auth.
    dependencies=[Depends(require_bearer_token)],
)
async def predict(
    payload: PredictionRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> PredictionResponse:
    model = request.app.state.loaded_model

    # Score first — fast, in-memory, no I/O.
    proba, pred = score(payload, model.pipeline, model.threshold)

    # Persist the prediction. The full request payload goes in as JSON so the
    # drift detector can compute distribution stats over it later. Storing the
    # *boolean* prediction and *probability* both means we can recompute the
    # threshold offline without re-running the model.
    row = Prediction(
        model_name=model.model_name,
        model_version=model.model_version,
        threshold=model.threshold,
        probability=proba,
        prediction=pred,
        request_payload=payload.model_dump(by_alias=True),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)  # populates row.id and row.created_at from the DB

    return PredictionResponse(
        prediction=pred,
        probability=proba,
        threshold=model.threshold,
        model_name=model.model_name,
        model_version=model.model_version,
        prediction_id=row.id,
        timestamp=row.created_at,
    )
