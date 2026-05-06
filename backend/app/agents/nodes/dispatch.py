from app.agents.state import InvestigationState


def dispatch_node(state: InvestigationState) -> dict:
    # No LLM — enqueues to Redis in Step 8
    return {}
