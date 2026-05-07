import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from langgraph.types import Command

from app.agents.llm import ActionOutput, CommsOutput, TriageOutput
from tests.conftest import make_session_factory

TRAJECTORIES = Path(__file__).parent.parent / "trajectories"

_COMMS_OUT = CommsOutput(
    summary="Drift detected in bank-churn v3. Investigation complete.",
    resolution="Action has been dispatched.",
)


async def _stream_nodes(
    graph: object, input_state: object, config: dict
) -> tuple[list[str], bool]:
    nodes: list[str] = []
    interrupted = False
    async for event in graph.astream(  # type: ignore[union-attr]
        input_state, config=config, stream_mode="updates"
    ):
        for key in event:
            if key == "__interrupt__":
                interrupted = True
            else:
                nodes.append(key)
    return nodes, interrupted


async def test_no_op_trajectory(graph, base_state, thread_config):
    triage_out = TriageOutput(verdict="no_drift", reasoning="PSI below threshold")
    comms_out = CommsOutput(
        summary="No real drift detected.", resolution="Monitoring continues."
    )
    snapshot = json.loads((TRAJECTORIES / "no_op.json").read_text())

    with (
        patch(
            "app.agents.nodes.triage.call_triage_llm",
            AsyncMock(return_value=triage_out),
        ),
        patch(
            "app.agents.nodes.comms.call_comms_llm",
            AsyncMock(return_value=comms_out),
        ),
    ):
        nodes, interrupted = await _stream_nodes(graph, base_state, thread_config)
        final = await graph.aget_state(thread_config)

    assert nodes == snapshot["nodes"]
    assert interrupted == snapshot["interrupted"]
    state = final.values
    assert state["triage_result"] == snapshot["expected_state"]["triage_result"]
    assert state["proposed_action"] == snapshot["expected_state"]["proposed_action"]
    assert state["dispatched"] == snapshot["expected_state"]["dispatched"]
    assert state["is_stale"] == snapshot["expected_state"]["is_stale"]
    assert state["summary"] is not None


async def test_replay_trajectory(graph, base_state, thread_config):
    triage_out = TriageOutput(verdict="real_drift", reasoning="PSI above threshold")
    action_out = ActionOutput(action="replay", reasoning="Replay test set to verify")
    snapshot = json.loads((TRAJECTORIES / "replay.json").read_text())

    with (
        patch(
            "app.agents.nodes.triage.call_triage_llm",
            AsyncMock(return_value=triage_out),
        ),
        patch(
            "app.agents.nodes.action.call_action_llm",
            AsyncMock(return_value=action_out),
        ),
        patch(
            "app.agents.nodes.comms.call_comms_llm",
            AsyncMock(return_value=_COMMS_OUT),
        ),
        patch("app.agents.nodes.dispatch.enqueue_job", return_value=True),
    ):
        nodes, interrupted = await _stream_nodes(graph, base_state, thread_config)
        final = await graph.aget_state(thread_config)

    assert nodes == snapshot["nodes"]
    assert interrupted == snapshot["interrupted"]
    state = final.values
    assert state["triage_result"] == snapshot["expected_state"]["triage_result"]
    assert state["proposed_action"] == snapshot["expected_state"]["proposed_action"]
    assert state["dispatched"] == snapshot["expected_state"]["dispatched"]
    assert state["is_stale"] == snapshot["expected_state"]["is_stale"]
    assert state["summary"] is not None


async def test_retrain_trajectory(graph, base_state, thread_config):
    triage_out = TriageOutput(
        verdict="real_drift", reasoning="PSI critical — retrain required"
    )
    action_out = ActionOutput(action="retrain", reasoning="Significant drift, retrain")
    snapshot = json.loads((TRAJECTORIES / "retrain.json").read_text())
    thread_config["configurable"]["session_factory"] = make_session_factory()

    with (
        patch(
            "app.agents.nodes.triage.call_triage_llm",
            AsyncMock(return_value=triage_out),
        ),
        patch(
            "app.agents.nodes.action.call_action_llm",
            AsyncMock(return_value=action_out),
        ),
        patch(
            "app.agents.nodes.comms.call_comms_llm",
            AsyncMock(return_value=_COMMS_OUT),
        ),
        patch("app.agents.nodes.dispatch.enqueue_job", return_value=True),
    ):
        phase1_nodes, interrupted = await _stream_nodes(
            graph, base_state, thread_config
        )
        assert phase1_nodes == snapshot["phase1_nodes"]
        assert interrupted == snapshot["interrupted"]

        phase2_nodes, _ = await _stream_nodes(
            graph,
            Command(resume={"approved": True, "approver_user_id": "test-approver"}),
            thread_config,
        )
        final = await graph.aget_state(thread_config)

    assert phase2_nodes == snapshot["phase2_nodes"]
    state = final.values
    assert state["triage_result"] == snapshot["expected_state"]["triage_result"]
    assert state["proposed_action"] == snapshot["expected_state"]["proposed_action"]
    assert state["dispatched"] == snapshot["expected_state"]["dispatched"]
    assert state["is_stale"] == snapshot["expected_state"]["is_stale"]
    assert state["summary"] is not None
    assert state["approver_user_id"] == "test-approver"
