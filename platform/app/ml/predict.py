"""Scoring logic. Engineers pdays into the two derived features and calls the pipeline."""

from typing import Any

import pandas as pd

from app.schemas.predict import PredictionRequest


def engineer_features(req: PredictionRequest) -> pd.DataFrame:
    """Turn validated API input into the single-row DataFrame the model expects."""
    # by_alias=True restores the dotted column names (emp.var.rate, etc.) that
    # the trained pipeline's ColumnTransformer looks for.
    raw = req.model_dump(by_alias=True)

    # Replicate the notebook's pdays engineering exactly. Same logic as cell 1.
    pdays = raw.pop("pdays")
    raw["was_contacted_before"] = int(pdays != 999)
    raw["days_since_contact"] = 0 if pdays == 999 else pdays

    return pd.DataFrame([raw])


def score(req: PredictionRequest, pipeline: Any, threshold: float) -> tuple[float, bool]:
    """Return (probability_of_positive, prediction_at_threshold)."""
    X = engineer_features(req)
    proba = float(pipeline.predict_proba(X)[0, 1])
    return proba, proba >= threshold
