"""MLflow stage transition. Single atomic write — promote target, archive whatever was Production."""

import structlog
import mlflow

from app.core.config import settings

logger = structlog.get_logger()


def promote_to_production(model_name: str, target_version: str) -> tuple[str, list[str]]:
    """
    Transition target_version to Production. archive_existing_versions=True
    ensures the singleton-Production invariant.

    Returns (promoted_version, archived_versions).
    """
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    client = mlflow.MlflowClient()

    currently_prod = [
        str(mv.version)
        for mv in client.search_model_versions(f"name='{model_name}'")
        if mv.current_stage == "Production"
    ]

    client.transition_model_version_stage(
        name=model_name,
        version=target_version,
        stage="Production",
        archive_existing_versions=True,
    )

    logger.info("promotion.complete", model_name=model_name, version=target_version, archived=currently_prod)
    return target_version, currently_prod
