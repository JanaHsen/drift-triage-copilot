"""
Lifespan handler — runs once at service startup and once at shutdown.

FastAPI calls the function below when the app starts. Anything yielded from it
becomes available on app.state during the request lifecycle. After yield runs,
the rest of the function executes at shutdown — that's where you close DB
connections, flush logs, etc.

Why an async context manager: the model loader, the DB engine, and any HTTP
clients we open here are expensive resources that should exist for the
service's whole lifetime, not be re-created per request. Loading them in
lifespan means startup pays the cost once.

"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # === Startup ===
    # TODO (next turn): load joblib model into app.state.model
    # TODO (next turn): load reference stats into app.state.reference_stats
    # TODO (next turn): create async SQLAlchemy engine into app.state.engine
    # TODO (next turn): create httpx.AsyncClient into app.state.http_client

    yield
    # === Shutdown ===
    # TODO (next turn): await app.state.engine.dispose()
    # TODO (next turn): await app.state.http_client.aclose()