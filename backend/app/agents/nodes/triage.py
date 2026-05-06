from langgraph.types import RunnableConfig

from app.agents.llm import LLMClient, call_triage_llm
from app.agents.state import InvestigationState


async def triage_node(state: InvestigationState, config: RunnableConfig) -> dict:
    client: LLMClient = config["configurable"]["llm_client"]
    result = await call_triage_llm(state, client)
    return {"triage_result": result.verdict}
