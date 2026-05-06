from app.agents.state import InvestigationState


def action_node(state: InvestigationState) -> dict:
    # Stub — real implementation uses LLM + interrupt() for HIL in Step 7
    return {"proposed_action": "no_op"}
