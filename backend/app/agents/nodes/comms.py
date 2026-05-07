import structlog
from langgraph.types import RunnableConfig

from app.agents.llm import LLMClient, call_comms_llm
from app.agents.state import InvestigationState


async def comms_node(state: InvestigationState, config: RunnableConfig) -> dict:
    logger = structlog.get_logger().bind(investigation_id=state["investigation_id"])
    client: LLMClient = config["configurable"]["llm_client"]
    logger.info("comms.start", proposed_action=state.get("proposed_action"))
    result = await call_comms_llm(state, client)
    logger.info("comms.complete")
    return {"summary": result.summary, "resolution": result.resolution}
