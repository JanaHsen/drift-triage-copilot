from langgraph.types import RunnableConfig

from app.agents.llm import LLMClient, call_action_llm
from app.agents.state import InvestigationState


async def action_node(state: InvestigationState, config: RunnableConfig) -> dict:
    client: LLMClient = config["configurable"]["llm_client"]
    result = await call_action_llm(state, client)
    return {"proposed_action": result.action}
