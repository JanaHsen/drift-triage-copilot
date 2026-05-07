"""
Model and reference-statistics loader.

Called once from lifespan at startup. Reads two artifacts off disk and bundles
them into a LoadedModel that gets stashed on app.state. Loading is slow
(joblib.load can take hundreds of ms on a calibrated pipeline); doing it once
at startup means request handlers never pay that cost.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadedModel:
    """
    Everything the platform needs to know about the loaded model.

    Frozen because it represents immutable startup-time state. If you need to
    swap the model in at runtime (rollback handler, future), build a new
    LoadedModel and replace the whole reference on app.state — never mutate.
    """

    # The fitted scikit-learn Pipeline (preprocessor + calibrated classifier).
    # Typed as Any so this module doesn't have to import sklearn.
    pipeline: Any

    # The operating threshold from the recall>=0.75 rule in the notebook.
    threshold: float

    # Identifiers that travel with every prediction response.
    model_name: str
    model_version: str

    # Frozen training distributions — used by the drift detector later.
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
    # Validate paths *before* loading — joblib's missing-file error is cryptic;
    # FileNotFoundError with a clear message points operators at the real fix.
    if not artifact_path.is_file():
        raise FileNotFoundError(
            f"Model artifact not found at {artifact_path}. "
            f"Check that ./platform/mlops is mounted into the container and the file exists."
        )
    if not reference_stats_path.is_file():
        raise FileNotFoundError(
            f"Reference stats not found at {reference_stats_path}. "
            f"Run cell 7 of the training notebook to write train_reference_stats.json."
        )

    logger.info("Loading model pipeline from %s", artifact_path)
    pipeline = joblib.load(artifact_path)

    logger.info("Loading reference stats from %s", reference_stats_path)
    reference_stats = json.loads(reference_stats_path.read_text(encoding="utf-8"))

    # Sanity-check the reference stats schema. If cell 7 of the notebook
    # changes shape, this fires a clear error pointing at the right source.
    if "numeric" not in reference_stats or "categorical" not in reference_stats:
        raise ValueError(
            f"Reference stats at {reference_stats_path} missing 'numeric' or "
            f"'categorical' top-level keys. The file may be corrupt or out of "
            f"sync with the training notebook."
        )

    logger.info(
        "Model loaded: %s v%s (threshold=%.4f, n_features=%d)",
        model_name,
        model_version,
        threshold,
        len(reference_stats["numeric"]) + len(reference_stats["categorical"]),
    )

    return LoadedModel(
        pipeline=pipeline,
        threshold=threshold,
        model_name=model_name,
        model_version=model_version,
        reference_stats=reference_stats,
    )
