from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI

from app.core.config import settings
from app.db.base import build_engine, build_session_factory

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    engine = build_engine(settings.database_url)
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)
    logger.info("app.startup")
    yield
    await engine.dispose()
    logger.info("app.shutdown")
