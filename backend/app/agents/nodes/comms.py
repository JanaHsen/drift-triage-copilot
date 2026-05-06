from langgraph.types import RunnableConfig

from app.agents.llm import LLMClient, call_comms_llm
from app.agents.state import InvestigationState


async def comms_node(state: InvestigationState, config: RunnableConfig) -> dict:
    client: LLMClient = config["configurable"]["llm_client"]
    result = await call_comms_llm(state, client)
    return {"summary": result.summary, "resolution": result.resolution}
