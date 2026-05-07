import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()


async def get_production_model_uri(model_name: str) -> str | None:
    """Return the platform's current model URI for model_name, or None if unreachable."""
    if not settings.platform_base_url:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.platform_base_url}/v1/model/info")
            resp.raise_for_status()
            data = resp.json()
            if data.get("model_name") == model_name:
                return str(data["model_uri"])
        return None
    except httpx.HTTPError as exc:
        logger.warning(
            "platform_reader.unreachable", error=str(exc), model_name=model_name
        )
        return None
