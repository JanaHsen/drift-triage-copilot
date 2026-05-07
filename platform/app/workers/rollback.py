import mlflow
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ActionJob

logger = structlog.get_logger()


async def handle_rollback(job: ActionJob, session: AsyncSession) -> dict:
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

    logger.info("rollback.complete", job_id=str(job.id), rolled_back_to=target_uri)
    return {
        "rolled_back_to": target_uri,
        "stage": "Production",
        "message": "previous Production versions archived in same transition",
    }
