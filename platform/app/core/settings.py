"""
Centralized configuration for the platform service.

Why pydantic-settings: it reads environment variables, validates types, and
supports loading from a .env file — all in one class. Compared to scattering
os.environ.get(...) calls across modules, this gives you a single source of
truth and a single place that fails loudly if a required variable is missing.

The pattern mirrors backend/app/core/settings.py exactly, with platform-specific
fields added. Both services read the SAME .env file, so identical field names
mean identical values automatically.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # The .env file lives at the repo root; SettingsConfigDict tries each path
    # in order and uses the first one that exists. The "../" entry is for the
    # case where alembic runs from inside platform/app/ — settings still finds
    # the env file one level up. extra="ignore" means env vars we don't declare
    # here don't crash the service (Rasha's keys won't trip us up).
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # Database — points at the same Postgres instance used but our tables
    # are namespaced separately (predictions, drift_snapshots, promotion_audit).
    # SQLAlchemy will not collide with her tables because table names are unique.
    database_url: str

    # Redis — used for the action dispatcher's job queue. Same instance as
    # Rasha's worker; we'll use a different key prefix to avoid collisions.
    redis_url: str

    # Bearer token shared between the two services for inter-service auth.
    # Set this to a long random string in .env. Empty default is intentional:
    # if it's missing, the auth dependency raises a clear startup error rather
    # than silently letting unauthenticated requests through.
    agent_token: str = ""

    # Where the agent's webhook receiver lives — the platform POSTs drift
    # events here. Inside docker-compose this is "http://backend:8000"; on the
    # host for manual testing it's "http://localhost:8000".
    agent_base_url: str = "http://backend:8000"

    # MLflow tracking URI. Defaults to a local file store so the service runs
    # without needing a separate MLflow container. Override in .env if you
    # spin up an MLflow service later.
    mlflow_tracking_uri: str = "file:./mlruns"

    # Drift detection knobs. Exposed as settings so we can tune them via .env
    # during the Friday demo without rebuilding the image.
    drift_window_size: int = 1000           # how many recent predictions to score
    drift_psi_threshold_medium: float = 0.1  # PSI bands from the literature
    drift_psi_threshold_high: float = 0.25
    drift_psi_threshold_critical: float = 0.5

    # Model artifact paths — mlops/ is where the training notebook writes its
    # outputs (joblib pipeline, JSON reference stats, model card). Mounted
    # into the container at /app/mlops via docker-compose.
    model_artifact_path: Path = Path("mlops/bank_marketing_classifier.joblib")
    reference_stats_path: Path = Path("mlops/train_reference_stats.json")


# Single shared instance. Importing settings.X anywhere in the codebase reads
# from this one validated object, not from os.environ directly.
settings = Settings()