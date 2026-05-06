from app.agents.state import InvestigationState


def comms_node(state: InvestigationState) -> dict:
    # Stub — real implementation uses LLM in Step 6
    return {
        "summary": "Investigation complete.",
        "resolution": "No action required.",
    }
