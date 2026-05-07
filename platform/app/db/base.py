"""SQLAlchemy declarative base and async engine factory."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """All platform-side ORM models inherit from this."""
    pass


def build_engine(database_url: str) -> AsyncEngine:
    # pool_pre_ping checks the connection before handing it out — protects
    # against stale connections after Postgres restarts.
    return create_async_engine(database_url, pool_pre_ping=True)
