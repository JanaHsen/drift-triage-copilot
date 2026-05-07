"""
Centralized configuration. Mirrors backend/app/core/settings.py for consistency
across the two services. All fields are read from environment variables, with
fallback to .env at repo root.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # extra="ignore" so backend-only env vars (OPENAI_API_KEY, etc.) don't
    # crash the platform's settings load.
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # ---- Infrastructure -----------------------------------------------------

    # Same Postgres instance as backend; our tables are namespaced separately
    # so there's no collision with investigations / hil_inbox / audit_log.
    database_url: str

    # Same Redis instance as backend; key prefixing handled in code later.
    redis_url: str

    # ---- Inter-service auth and routing -------------------------------------

    # Bearer token shared with the agent. Empty default is intentional: the
    # auth dependency rejects every request when this is unset, which is the
    # safer failure mode than letting unauthenticated traffic through.
    agent_token: str = ""

    # Base URL of Rasha's webhook receiver. Inside docker-compose the host is
    # "backend"; on the host machine it's "localhost:8000".
    agent_base_url: str = "http://backend:8000"

    # ---- MLflow -------------------------------------------------------------

    # Local file store by default, no separate MLflow service required.
    mlflow_tracking_uri: str = "file:./mlruns"

    # ---- Model artifacts ----------------------------------------------------

    # Paths inside the container; the host's ./platform/mlops is mounted at
    # /app/mlops via docker-compose, so these resolve correctly.
    model_artifact_path: Path = Path("mlops/bank_marketing_classifier.joblib")
    reference_stats_path: Path = Path("mlops/train_reference_stats.json")

    # Identifiers that ride along with every prediction response. Update when
    # registering a new version in MLflow.
    model_name: str = "bank-marketing-classifier"
    model_version: str = "v0.1.0-week5"

    # Operating threshold from cell 5 of the notebook (recall>=0.75 rule).
    # Verify this matches your model_card.md; override via OPERATING_THRESHOLD
    # in .env to experiment without code changes.
    operating_threshold: float = 0.070

    # ---- Drift detection knobs ----------------------------------------------

    # Tuned in later turns; defaults are the conventional PSI bands from the
    # MLOps literature.
    drift_window_size: int = 1000
    drift_psi_threshold_medium: float = 0.1
    drift_psi_threshold_high: float = 0.25
    drift_psi_threshold_critical: float = 0.5


# Single shared instance imported elsewhere as `from app.core.settings import settings`.
settings = Settings()
