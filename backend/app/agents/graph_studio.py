"""
Dev-only graph export for LangGraph Studio.
Uses MemorySaver so Studio can load it without a live Postgres connection.
Rebuilds the graph inline to avoid importing AsyncPostgresSaver at module level.
Not imported by the production app.
"""

from langgraph.graph import END, StateGraph

from app.agents.nodes.action import action_node
from app.agents.nodes.comms import comms_node
from app.agents.nodes.dispatch import dispatch_node
from app.agents.nodes.triage import triage_node
from app.agents.state import InvestigationState
from app.agents.supervisor import supervisor_node

_builder = StateGraph(InvestigationState)
_builder.add_node("supervisor", supervisor_node)
_builder.add_node("triage", triage_node)
_builder.add_node("action", action_node)
_builder.add_node("comms", comms_node)
_builder.add_node("dispatch", dispatch_node)
_builder.set_entry_point("supervisor")

for _node in ["triage", "action", "comms", "dispatch"]:
    _builder.add_edge(_node, "supervisor")

_builder.add_conditional_edges(
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

graph = _builder.compile()
