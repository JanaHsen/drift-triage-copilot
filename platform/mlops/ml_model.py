import json
from pathlib import Path

import joblib
import mlflow
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

HERE = Path(__file__).parent
DATA_PATH = HERE / "bank-additional-full.csv"
ARTIFACT_PATH = HERE / "bank_marketing_classifier.joblib"
BASELINE_PATH = HERE / "train_reference_stats.json"

NUMERIC_COLS = [
    "age", "campaign", "previous",
    "was_contacted_before", "days_since_contact",
    "emp.var.rate", "cons.price.idx", "cons.conf.idx",
    "euribor3m", "nr.employed",
]
CATEGORICAL_COLS = [
    "job", "marital", "education", "default", "housing", "loan",
    "contact", "month", "day_of_week", "poutcome",
]
RECALL_FLOOR = 0.75
RANDOM_STATE = 42


def load_and_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";")

    # duration leaks the target — only known after the call ends
    df = df.drop(columns=["duration"])

    # pdays == 999 is a sentinel for "never contacted before"; split into flag + numeric
    df["was_contacted_before"] = (df["pdays"] != 999).astype(int)
    df["days_since_contact"] = df["pdays"].where(df["pdays"] != 999, other=0)
    df = df.drop(columns=["pdays"])

    df["y"] = df["y"].map({"no": 0, "yes": 1})
    return df


def split(df: pd.DataFrame):
    X = df.drop(columns=["y"])
    y = df["y"]

    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=RANDOM_STATE,
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=0.25, stratify=y_temp, random_state=RANDOM_STATE,
    )
    return X_train, X_val, X_test, y_train, y_val, y_test


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC_COLS),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLS),
    ])
    classifier = HistGradientBoostingClassifier(
        class_weight="balanced", random_state=RANDOM_STATE,
    )
    return Pipeline([("preprocess", preprocessor), ("classifier", classifier)])


def choose_threshold(y_true, proba, recall_floor: float = RECALL_FLOOR) -> float:
    sweep = np.linspace(0.01, 0.99, 99)
    recalls = np.array([recall_score(y_true, proba >= t) for t in sweep])
    valid = recalls >= recall_floor
    if not valid.any():
        raise ValueError(f"No threshold meets recall floor {recall_floor}")
    return float(sweep[valid].max())


def evaluate(name: str, X, y, pipeline: Pipeline, threshold: float) -> dict:
    proba = pipeline.predict_proba(X)[:, 1]
    pred = (proba >= threshold).astype(int)
    metrics = {
        "split": name,
        "auc": roc_auc_score(y, proba),
        "f1": f1_score(y, pred),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred),
    }
    print(f"{name:5s} | AUC={metrics['auc']:.4f}  F1={metrics['f1']:.4f}  "
          f"P={metrics['precision']:.4f}  R={metrics['recall']:.4f}")
    return metrics


def build_reference_stats(X_train: pd.DataFrame, pipeline, threshold: float) -> dict:
    baseline = {"n_train": int(len(X_train)), "numeric": {}, "categorical": {}}

    for c in NUMERIC_COLS:
        s = X_train[c]
        edges = np.linspace(s.min(), s.max(), 11).tolist()
        counts, _ = np.histogram(s.values, bins=edges)
        baseline["numeric"][c] = {
            "mean": float(s.mean()),
            "std": float(s.std()),
            "p10": float(s.quantile(0.10)),
            "p50": float(s.quantile(0.50)),
            "p90": float(s.quantile(0.90)),
            "min": float(s.min()),
            "max": float(s.max()),
            "bin_edges": edges,
            "frequencies": (counts / len(s)).tolist(),
        }

    for c in CATEGORICAL_COLS:
        counts = X_train[c].value_counts(normalize=True).to_dict()
        baseline["categorical"][c] = {k: float(v) for k, v in counts.items()}

    proba_train = pipeline.predict_proba(X_train)[:, 1]
    out_edges = np.linspace(0.0, 1.0, 11).tolist()
    out_counts, _ = np.histogram(proba_train, bins=out_edges)
    baseline["output_distribution"] = {
        "bin_edges": out_edges,
        "frequencies": (out_counts / len(proba_train)).tolist(),
    }

    return baseline


def main() -> None:
    df = load_and_clean(DATA_PATH)
    X_train, X_val, X_test, y_train, y_val, y_test = split(df)

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    proba_val = pipeline.predict_proba(X_val)[:, 1]
    threshold = choose_threshold(y_val, proba_val)
    print(f"Operating threshold (recall ≥ {RECALL_FLOOR}): {threshold:.3f}\n")

    evaluate("train", X_train, y_train, pipeline, threshold)
    evaluate("val", X_val, y_val, pipeline, threshold)
    evaluate("test", X_test, y_test, pipeline, threshold)

    joblib.dump(pipeline, ARTIFACT_PATH)
    print(f"\nSaved pipeline: {ARTIFACT_PATH}")

    BASELINE_PATH.write_text(
        json.dumps(build_reference_stats(X_train, pipeline, threshold), indent=2),
        encoding="utf-8",
    )
    print(f"Saved reference stats: {BASELINE_PATH}")

    mlflow.set_tracking_uri("file:./mlruns")
    mlflow.set_experiment("baseline-training")
    with mlflow.start_run(run_name="baseline"):
        mlflow.log_metric("val_recall", float(recall_score(y_val, (pipeline.predict_proba(X_val)[:, 1] >= threshold).astype(int))))
        mlflow.log_param("operating_threshold", threshold)
        mlflow.log_param("random_state", RANDOM_STATE)
        mv = mlflow.sklearn.log_model(
            pipeline,
            artifact_path="model",
            registered_model_name="bank-marketing-classifier",
        )
    print(f"\nRegistered baseline in MLflow: models:/bank-marketing-classifier/{mv.registered_model_version}")
    print(f"Set MODEL_VERSION={mv.registered_model_version} in config or .env")


if __name__ == "__main__":
    main()
