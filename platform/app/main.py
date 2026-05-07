"""
FastAPI application entry point.

This module's only job is composition: instantiate the app, attach the
lifespan handler, register every router.

"""

from fastapi import FastAPI

from app.core.lifespan import lifespan
from app.routers import health

app = FastAPI(
    title="Drift Triage Co-Pilot — Platform",
    description="Model serving, drift detection, and promotion gate.",
    version="0.1.0",
    lifespan=lifespan,
)

# Register routers. As we add predict, actions, and promote, each gets a line
# below this one. The order doesn't matter functionally but keep it sorted by
# the order routes appear in the URL tree to make this file pleasant to read.
app.include_router(health.router)
# app.include_router(predict.router)   # next turn
# app.include_router(actions.router)   # later
# app.include_router(promote.router)   # last