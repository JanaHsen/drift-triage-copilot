import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from langgraph.checkpoint.memory import MemorySaver

from app.agents.graph import build_graph


@pytest.fixture
def graph():
    return build_graph(MemorySaver())


@pytest.fixture
def thread_config():
    return {
        "configurable": {
            "thread_id": str(uuid.uuid4()),
            "llm_client": MagicMock(),
            "session_factory": None,
        }
    }


@pytest.fixture
def base_state():
    return {
        "investigation_id": str(uuid.uuid4()),
        "event_id": "test-event-001",
        "model_name": "bank-churn",
        "model_version": "v3",
        "model_uri_at_open": "models:/bank-churn/3",
        "severity": "high",
        "previous_severity": "medium",
        "drift_summary": {
            "psi_features": {"age": 0.18, "balance": 0.22},
            "chi2_features": {"job": 0.05},
            "output_distribution_drift": 0.15,
        },
        "triage_result": None,
        "proposed_action": None,
        "idempotency_key": None,
        "approver_user_id": None,
        "is_stale": False,
        "dispatched": False,
        "summary": None,
        "resolution": None,
        "next": "",
    }


def make_session_factory() -> object:
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    @asynccontextmanager
    async def factory():  # type: ignore[misc]
        yield mock_session

    return factory
