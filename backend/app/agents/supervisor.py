from langgraph.graph import END

from app.agents.state import InvestigationState


def supervisor_node(state: InvestigationState) -> dict:
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
