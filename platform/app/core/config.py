from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str
    redis_url: str

    # Empty default — auth rejects all requests when unset, safer than open access.
    agent_token: str = ""

    agent_base_url: str = "http://localhost:8000"
    mlflow_tracking_uri: str = "file:./mlruns"

    model_artifact_path: Path = Path("mlops/bank_marketing_classifier.joblib")
    reference_stats_path: Path = Path("mlops/train_reference_stats.json")
    model_name: str = "bank-marketing-classifier"
    model_version: str = "2"
    operating_threshold: float = 0.070

    drift_window_size: int = 1000
    drift_psi_threshold_medium: float = 0.1
    drift_psi_threshold_high: float = 0.25
    drift_psi_threshold_critical: float = 0.5

    replay_window_size: int = 100
    training_data_path: Path = Path("mlops/bank-additional-full.csv")
    drift_check_interval_seconds: int = 600


settings = Settings()
