import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class LoadedModel:
    """Bundle of loaded model artifacts, immutable after startup."""

    pipeline: Any
    threshold: float
    model_name: str
    model_version: str
    reference_stats: dict


def load_model(
    artifact_path: Path,
    reference_stats_path: Path,
    *,
    threshold: float,
    model_name: str,
    model_version: str,
) -> LoadedModel:
    """Read both artifacts off disk and return a LoadedModel bundle."""
    # Validate paths before loading — joblib's missing-file error is cryptic.
    if not artifact_path.is_file():
        raise FileNotFoundError(
            f"Model artifact not found at {artifact_path}. "
            f"Check that ./platform/mlops is mounted into the container and the file exists."
        )
    if not reference_stats_path.is_file():
        raise FileNotFoundError(
            f"Reference stats not found at {reference_stats_path}. "
            f"Run ml_model.py to generate train_reference_stats.json."
        )

    pipeline = joblib.load(artifact_path)
    reference_stats = json.loads(reference_stats_path.read_text(encoding="utf-8"))

    # Sanity-check the reference stats schema — guards against a stale file.
    if "numeric" not in reference_stats or "categorical" not in reference_stats:
        raise ValueError(
            f"Reference stats at {reference_stats_path} missing 'numeric' or "
            f"'categorical' top-level keys."
        )

    logger.info(
        "model.loaded",
        model_name=model_name,
        model_version=model_version,
        threshold=threshold,
        n_features=len(reference_stats["numeric"]) + len(reference_stats["categorical"]),
    )

    return LoadedModel(
        pipeline=pipeline,
        threshold=threshold,
        model_name=model_name,
        model_version=model_version,
        reference_stats=reference_stats,
    )
