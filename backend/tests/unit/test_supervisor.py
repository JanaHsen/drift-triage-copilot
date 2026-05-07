from unittest.mock import AsyncMock, patch

import pytest
from langgraph.graph import END

from app.agents.supervisor import supervisor_node

_CONFIG = {}


def _state(**overrides):
    base = {
        "investigation_id": "inv-001",
        "event_id": "evt-001",
        "model_name": "bank-churn",
        "model_version": "v3",
        "model_uri_at_open": "models:/bank-churn/3",
        "severity": "high",
        "previous_severity": "medium",
        "drift_summary": {},
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
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def mock_platform_reader():
    # Return None so stale-check always passes in unit tests.
    with patch(
        "app.agents.supervisor.get_production_model_uri",
        new_callable=AsyncMock,
        return_value=None,
    ):
        yield


@pytest.mark.asyncio
async def test_supervisor_routes_to_triage_first():
    assert (await supervisor_node(_state(), _CONFIG))["next"] == "triage"


@pytest.mark.asyncio
async def test_supervisor_routes_to_action_on_real_drift():
    assert (await supervisor_node(_state(triage_result="real_drift"), _CONFIG))["next"] == "action"


@pytest.mark.asyncio
async def test_supervisor_routes_to_comms_on_no_drift():
    assert (await supervisor_node(_state(triage_result="no_drift"), _CONFIG))["next"] == "comms"


@pytest.mark.asyncio
async def test_supervisor_ends_after_no_drift_comms():
    result = await supervisor_node(_state(triage_result="no_drift", summary="done"), _CONFIG)
    assert result["next"] == END


@pytest.mark.asyncio
async def test_supervisor_routes_to_dispatch_when_not_dispatched():
    result = await supervisor_node(_state(
        triage_result="real_drift",
        proposed_action="retrain",
        dispatched=False,
    ), _CONFIG)
    assert result["next"] == "dispatch"


@pytest.mark.asyncio
async def test_supervisor_routes_to_comms_after_dispatch():
    result = await supervisor_node(_state(
        triage_result="real_drift",
        proposed_action="retrain",
        dispatched=True,
    ), _CONFIG)
    assert result["next"] == "comms"


@pytest.mark.asyncio
async def test_supervisor_ends_after_real_drift_comms():
    result = await supervisor_node(_state(
        triage_result="real_drift",
        proposed_action="retrain",
        dispatched=True,
        summary="done",
    ), _CONFIG)
    assert result["next"] == END


@pytest.mark.asyncio
async def test_supervisor_ends_when_stale():
    assert (await supervisor_node(_state(is_stale=True), _CONFIG))["next"] == END


@pytest.mark.asyncio
async def test_supervisor_no_op_skips_dispatch():
    result = await supervisor_node(_state(
        triage_result="real_drift",
        proposed_action="no_op",
        dispatched=False,
    ), _CONFIG)
    assert result["next"] == "comms"
