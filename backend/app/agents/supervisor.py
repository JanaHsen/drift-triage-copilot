import structlog
from langgraph.graph import END
from langgraph.types import RunnableConfig

from app.agents.state import InvestigationState
from app.services.platform_reader import get_production_model_uri

logger = structlog.get_logger()


async def supervisor_node(state: InvestigationState, config: RunnableConfig) -> dict:
    current_uri = await get_production_model_uri(state["model_name"])
    if current_uri is not None and current_uri != state["model_uri_at_open"]:
        logger.warning(
            "supervisor.stale",
            investigation_id=state["investigation_id"],
            uri_at_open=state["model_uri_at_open"],
            current_uri=current_uri,
        )
        return {"next": END, "is_stale": True}

    if state.get("is_stale"):
        return {"next": END}

    if state.get("triage_result") is None:
        return {"next": "triage"}

    if state["triage_result"] == "no_drift":
        if state.get("summary") is None:
            return {"next": "comms"}
        return {"next": END}

    if state["triage_result"] == "real_drift":
        if state.get("proposed_action") is None:
            return {"next": "action"}

        if state["proposed_action"] != "no_op" and not state.get("dispatched"):
            return {"next": "dispatch"}

        if state.get("summary") is None:
            return {"next": "comms"}
        return {"next": END}

    return {"next": END}
