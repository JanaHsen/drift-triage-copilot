from typing import Any, AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with request.app.state.session_factory() as session:
        yield session


def get_graph(request: Request) -> Any:
    return request.app.state.graph


def get_llm_client(request: Request) -> Any:
    return request.app.state.llm_client


def get_session_factory(request: Request) -> Any:
    return request.app.state.session_factory
