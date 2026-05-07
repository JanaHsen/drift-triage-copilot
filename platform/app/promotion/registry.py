"""MLflow stage transition. Single atomic write — promote target, archive whatever was Production."""

import logging

import mlflow

from app.core.settings import settings

logger = logging.getLogger(__name__)


def promote_to_production(model_name: str, target_version: str) -> tuple[str, list[str]]:
    """
    Transition target_version to Production. archive_existing_versions=True
    ensures the singleton-Production invariant.

    Returns (promoted_version, archived_versions).
    """
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    client = mlflow.MlflowClient()

    # Capture what's currently Production BEFORE the transition so we can report it accurately.
    # str() coerces because the file-store backend returns versions as int while
    # the REST backend returns them as str — contract requires list[str].
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

    logger.info(
        "Promoted %s v%s to Production. Archived: %s",
        model_name, target_version, currently_prod,
    )
    return target_version, currently_prod
