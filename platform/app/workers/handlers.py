"""Action handlers — execute replay/retrain/rollback jobs."""

import logging
from datetime import datetime, timezone
from pathlib import Path

import joblib
import mlflow
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.db.models import ActionJob, Prediction
from app.ml.predict import engineer_features
from app.schemas.predict import PredictionRequest

logger = logging.getLogger(__name__)


async def handle_replay(job: ActionJob, session: AsyncSession) -> dict:
    """
    Re-score the last N predictions with the current model. Asserts byte-level
    reproducibility (|new - old| < 1e-12) — the brief's '1e-12 fidelity'
    requirement.
    """
    REPLAY_N = 100
    pipeline = joblib.load(settings.model_artifact_path)

    stmt = (
        select(Prediction)
        .where(Prediction.model_name == settings.model_name)
        .order_by(Prediction.created_at.desc())
        .limit(REPLAY_N)
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
            if len(mismatches) < 5:  # cap details for log size
                mismatches.append({"id": str(p.id), "old": p.probability, "new": new_proba})

    return {
        "replayed": len(predictions),
        "matched": matched,
        "mismatched": mismatched,
        "fidelity_passed": mismatched == 0,
        "sample_mismatches": mismatches,
    }


async def handle_retrain(job: ActionJob, session: AsyncSession) -> dict:
    """
    Refit the same pipeline architecture on current training data. Registers
    as a new MLflow version. Does NOT auto-promote — promotion goes through
    /v1/promote with the day-4 checklist.
    """
    data_path = Path("mlops/bank-additional-full.csv")
    if not data_path.is_file():
        raise FileNotFoundError(f"Training data not found at {data_path}")

    # Replicate the notebook's preprocessing exactly so the new model has the
    # same feature schema as the live one.
    df = pd.read_csv(data_path, sep=";")
    df = df.drop(columns=["duration"])
    df["was_contacted_before"] = (df["pdays"] != 999).astype(int)
    df["days_since_contact"] = df["pdays"].where(df["pdays"] != 999, 0)
    df = df.drop(columns=["pdays"])
    df["y"] = (df["y"] == "yes").astype(int)

    X = df.drop(columns=["y"])
    y = df["y"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = X.select_dtypes(include=["object"]).columns.tolist()

    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), numeric_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols),
    ])
    # Match the notebook's winner exactly: raw HistGradientBoosting with
    # balanced class weights (notebook had USE_CALIBRATED=False). Diverging
    # from this is what made our recall come in below the 0.75 floor.
    pipeline = Pipeline([
        ("preprocess", preprocessor),
        ("classifier", HistGradientBoostingClassifier(
            class_weight="balanced", random_state=42,
        )),
    ])
    pipeline.fit(X_train, y_train)
    test_score = float(pipeline.score(X_test, y_test))

    # Recall — the metric the promotion gate actually checks against the
    # 0.75 floor. Compute at the live operating threshold from settings,
    # not at the default 0.5 (which would be near-zero on this imbalanced
    # dataset and look like a regression even when the model is fine).
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    threshold = settings.operating_threshold
    y_pred_at_threshold = (y_proba >= threshold).astype(int)
    test_recall = float(recall_score(y_test, y_pred_at_threshold))
    recall_default = float(recall_score(y_test, pipeline.predict(X_test)))

    # Candidate filename — does NOT overwrite the live artifact. Promotion
    # is what makes the candidate live.
    candidate_path = Path(f"mlops/bank_marketing_classifier_candidate_{job.id}.joblib")
    joblib.dump(pipeline, candidate_path)

    # Register new MLflow version under the same name.
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    # set_experiment() creates the named experiment if it doesn't exist —
    # required when mlruns/ is freshly mounted and has no Default experiment.
    mlflow.set_experiment("platform-retrain")
    with mlflow.start_run(run_name=f"retrain-{job.id}"):
        mlflow.log_metric("test_accuracy", test_score)
        mlflow.log_metric("test_recall", test_recall)              # recall at live operating threshold
        mlflow.log_metric("recall_at_threshold", test_recall)      # alias the checklist also accepts
        mlflow.log_metric("recall_default_threshold", recall_default)
        mlflow.log_param("operating_threshold", threshold)
        mlflow.log_param("trigger", "platform_retrain_job")
        mlflow.log_param("job_id", str(job.id))
        mlflow.sklearn.log_model(
            pipeline,
            artifact_path="model",
            registered_model_name=settings.model_name,
        )

    return {
        "candidate_artifact": str(candidate_path),
        "test_accuracy": test_score,
        "test_recall_at_threshold": test_recall,
        "operating_threshold": threshold,
        "registered_as": f"models:/{settings.model_name}/latest",
        "message": "candidate registered; promote via /v1/promote to make live",
    }


async def handle_rollback(job: ActionJob, session: AsyncSession) -> dict:
    """
    Transition the target model version back to Production. Whatever's
    currently Production gets archived atomically (archive_existing_versions=True
    avoids two-Production-versions ambiguity).
    """
    target_uri = job.target_model_uri
    if not target_uri.startswith("models:/"):
        raise ValueError(f"Invalid target_model_uri for rollback: {target_uri}")
    parts = target_uri.removeprefix("models:/").split("/")
    if len(parts) != 2:
        raise ValueError(f"Cannot parse name/version from {target_uri}")
    name, version = parts

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    client = mlflow.MlflowClient()
    client.transition_model_version_stage(
        name=name,
        version=version,
        stage="Production",
        archive_existing_versions=True,
    )

    return {
        "rolled_back_to": target_uri,
        "stage": "Production",
        "message": "previous Production versions archived in same transition",
    }


HANDLERS = {
    "replay": handle_replay,
    "retrain": handle_retrain,
    "rollback": handle_rollback,
}
