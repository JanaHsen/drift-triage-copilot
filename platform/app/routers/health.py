"""
Health endpoint — for docker-compose's healthcheck and for humans poking the
service. Returns 200 if the process is up and serving requests.

Notably this endpoint is NOT behind auth. Healthchecks need to work without
credentials (docker-compose runs them from inside the container network), and
exposing whether the service is alive is not a security risk.

"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}