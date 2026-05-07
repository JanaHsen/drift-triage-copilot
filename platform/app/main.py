from fastapi import FastAPI

from app.core.lifespan import lifespan
from app.routers import actions, drift, health, predict, promote

app = FastAPI(
    title="Drift Triage Co-Pilot — Platform",
    description="Model serving, drift detection, action dispatch, promotion gate.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(predict.router)
app.include_router(drift.router)
app.include_router(actions.router)
app.include_router(promote.router)
