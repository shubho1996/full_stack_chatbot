"""
LangGraph graph definition for the ReAct agent.

Graph shape
-----------

    START
      │
      ▼
   planner          Classify complexity → set max_retries
      │
      ▼
    agent   ◄─────────────────────────────────────┐
      │                                            │
      ▼                                            │
  _route_after_agent                              │
      │                                            │
      ├─── "tools" ──► tools ──────────────────────┘
      │
      └─── END

Routing logic (_route_after_agent)
-----------------------------------
  • If the last AIMessage contains tool_calls AND retry_count < max_retries
    → route to "tools" (execute tools, come back to agent)
  • Otherwise → END (stream final answer to user)

In Stage 4 (TOOLS = []) the agent never produces tool_calls, so the
graph always goes agent → END on the first pass.
In Stage 5+ real tools are registered and the loop becomes active.
"""

from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph

from .nodes import agent_node, planner_node, tools_node
from .state import AgentState


def _route_after_agent(state: AgentState) -> str:
    last = state["messages"][-1]
    has_tool_calls = isinstance(last, AIMessage) and bool(last.tool_calls)
    under_budget = state.get("retry_count", 0) < state.get("max_retries", 1)

    if has_tool_calls and under_budget:
        return "tools"
    return END


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("planner", planner_node)
    g.add_node("agent", agent_node)
    g.add_node("tools", tools_node)

    g.set_entry_point("planner")
    g.add_edge("planner", "agent")
    g.add_conditional_edges(
        "agent",
        _route_after_agent,
        {"tools": "tools", END: END},
    )
    g.add_edge("tools", "agent")

    return g.compile()


# Module-level singleton — import this in the FastAPI router
graph = build_graph()
