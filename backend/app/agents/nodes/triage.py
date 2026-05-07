import structlog
from langgraph.types import RunnableConfig

from app.agents.llm import LLMClient, call_triage_llm
from app.agents.state import InvestigationState


async def triage_node(state: InvestigationState, config: RunnableConfig) -> dict:
    logger = structlog.get_logger().bind(investigation_id=state["investigation_id"])
    client: LLMClient = config["configurable"]["llm_client"]
    logger.info("triage.start", severity=state["severity"])
    result = await call_triage_llm(state, client)
    logger.info("triage.complete", verdict=result.verdict)
    return {"triage_result": result.verdict}
