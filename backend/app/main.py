from fastapi import FastAPI

from app.core.lifespan import lifespan
from app.routers import health, webhook_receiver

app = FastAPI(title="Drift Triage Co-Pilot", lifespan=lifespan)

app.include_router(health.router)
app.include_router(webhook_receiver.router)
