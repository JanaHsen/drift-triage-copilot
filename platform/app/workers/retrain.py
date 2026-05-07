from pathlib import Path

import joblib
import mlflow
import numpy as np
import pandas as pd
import structlog
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ActionJob

logger = structlog.get_logger()

async def handle_retrain(job: ActionJob, session: AsyncSession) -> dict:
    if not settings.training_data_path.is_file():
        raise FileNotFoundError(f"Training data not found at {settings.training_data_path}")

    df = pd.read_csv(settings.training_data_path, sep=";")
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
    pipeline = Pipeline([
        ("preprocess", preprocessor),
        ("classifier", HistGradientBoostingClassifier(
            class_weight="balanced", random_state=42,
        )),
    ])
    pipeline.fit(X_train, y_train)
    test_score = float(pipeline.score(X_test, y_test))

    y_proba = pipeline.predict_proba(X_test)[:, 1]
    threshold = settings.operating_threshold
    y_pred_at_threshold = (y_proba >= threshold).astype(int)
    test_recall = float(recall_score(y_test, y_pred_at_threshold))
    recall_default = float(recall_score(y_test, pipeline.predict(X_test)))

    candidate_path = Path(f"mlops/bank_marketing_classifier_candidate_{job.id}.joblib")
    joblib.dump(pipeline, candidate_path)

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment("platform-retrain")
    with mlflow.start_run(run_name=f"retrain-{job.id}"):
        mlflow.log_metric("test_accuracy", test_score)
        mlflow.log_metric("test_recall", test_recall)
        mlflow.log_metric("recall_at_threshold", test_recall)
        mlflow.log_metric("recall_default_threshold", recall_default)
        mlflow.log_param("operating_threshold", threshold)
        mlflow.log_param("trigger", "platform_retrain_job")
        mlflow.log_param("job_id", str(job.id))
        mlflow.sklearn.log_model(
            pipeline,
            artifact_path="model",
            registered_model_name=settings.model_name,
        )

    logger.info("retrain.complete", job_id=str(job.id), test_accuracy=test_score, test_recall=test_recall)
    return {
        "candidate_artifact": str(candidate_path),
        "test_accuracy": test_score,
        "test_recall_at_threshold": test_recall,
        "operating_threshold": threshold,
        "registered_as": f"models:/{settings.model_name}/latest",
        "message": "candidate registered; promote via /v1/promote to make live",
    }
