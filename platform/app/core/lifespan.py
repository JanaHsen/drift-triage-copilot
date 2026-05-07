import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

import structlog

import app.db  # noqa: F401  — registers models with Base.metadata
from app.core.config import settings
from app.db.base import Base, build_engine
from app.ml.loader import load_model
from app.queue import build_redis_client

logger = structlog.get_logger()


async def _drift_check_loop(app: FastAPI) -> None:
    from app.drift.orchestrator import run_drift_check

    await asyncio.sleep(settings.drift_check_interval_seconds)
    while True:
        try:
            session_factory = app.state.session_factory
            async with session_factory() as session:
                snapshot = await run_drift_check(
                    session=session,
                    http_client=app.state.http_client,
                    loaded_model=app.state.loaded_model,
                )
            logger.info(
                "drift.auto_check",
                severity=snapshot.severity,
                webhook_emitted=snapshot.webhook_emitted,
            )
        except ValueError:
            logger.debug("drift.auto_check.skipped", reason="no predictions in window")
        except Exception as exc:
            logger.error("drift.auto_check.error", error=str(exc))
        await asyncio.sleep(settings.drift_check_interval_seconds)


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

    drift_task = asyncio.create_task(_drift_check_loop(app))
    logger.info("drift.auto_check.started", interval_seconds=settings.drift_check_interval_seconds)

    yield

    # ---- Shutdown ----
    logger.info("Platform service shutting down...")
    drift_task.cancel()
    await app.state.http_client.aclose()
    await app.state.redis_client.aclose()
    await app.state.engine.dispose()
