from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.lifespan import lifespan
from app.observability.logging import configure_logging
from app.observability.tracing import configure_tracing
from app.routers import health, hil, investigations, queue, webhook_receiver

configure_logging()
configure_tracing()

app = FastAPI(title="Drift Triage Co-Pilot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://frontend:8501"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health.router)
app.include_router(webhook_receiver.router)
app.include_router(hil.router)
app.include_router(investigations.router)
app.include_router(queue.router)
