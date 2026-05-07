"""Startup/shutdown — model, DB engine, tables, HTTP client, Redis client."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

import app.db  # noqa: F401  — registers models with Base.metadata
from app.core.settings import settings
from app.db.base import Base, build_engine
from app.ml.loader import load_model
from app.queue.client import build_redis_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # ---- Startup ----
    logger.info("Platform service starting up...")

    app.state.loaded_model = load_model(
        artifact_path=settings.model_artifact_path,
        reference_stats_path=settings.reference_stats_path,
        threshold=settings.operating_threshold,
        model_name=settings.model_name,
        model_version=settings.model_version,
    )

    engine = build_engine(settings.database_url)
    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Platform tables ensured (predictions, drift_snapshots, action_jobs, promotion_audit)")

    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    app.state.redis_client = build_redis_client(settings.redis_url)
    logger.info("HTTP client and Redis client ready")

    yield

    # ---- Shutdown ----
    logger.info("Platform service shutting down...")
    await app.state.http_client.aclose()
    await app.state.redis_client.aclose()
    await app.state.engine.dispose()
