from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.agents.graph import build_graph
from app.core.config import settings
from app.db.base import build_engine, build_session_factory

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # SQLAlchemy engine — used by route handlers for our app tables
    engine = build_engine(settings.database_url)
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)

    # Psycopg pool — used by LangGraph's Postgres checkpointer (separate from SQLAlchemy)
    psycopg_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    async with AsyncConnectionPool(
        conninfo=psycopg_url,
        max_size=10,
        kwargs={"autocommit": True, "prepare_threshold": 0},
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        app.state.graph = build_graph(checkpointer)
        logger.info("app.startup")
        yield
        logger.info("app.shutdown")

    await engine.dispose()
