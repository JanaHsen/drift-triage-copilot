from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph

from app.agents.nodes.action import action_node
from app.agents.nodes.comms import comms_node
from app.agents.nodes.dispatch import dispatch_node
from app.agents.nodes.triage import triage_node
from app.agents.state import InvestigationState
from app.agents.supervisor import supervisor_node


def build_graph(checkpointer: AsyncPostgresSaver) -> StateGraph:
    graph = StateGraph(InvestigationState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("triage", triage_node)
    graph.add_node("action", action_node)
    graph.add_node("comms", comms_node)
    graph.add_node("dispatch", dispatch_node)

    graph.set_entry_point("supervisor")

    # Every sub-agent returns to supervisor when done
    for node in ["triage", "action", "comms", "dispatch"]:
        graph.add_edge(node, "supervisor")

    # Supervisor routes based on state["next"]
    graph.add_conditional_edges(
        "supervisor",
        lambda state: state["next"],
        {
            "triage": "triage",
            "action": "action",
            "comms": "comms",
            "dispatch": "dispatch",
            END: END,
        },
    )

    return graph.compile(checkpointer=checkpointer)
