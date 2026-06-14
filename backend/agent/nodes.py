"""
Node implementations for the ReAct agent graph.

agent_node  — Core reasoning loop: generates text or tool calls.
tools_node  — Executes tool calls with call-log deduplication.

Each node receives the full AgentState and returns a *partial* state
dict — only the keys it wants to update.  LangGraph merges these
updates (using reducers where defined, e.g. add_messages for messages).
"""

import json
from functools import lru_cache

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from .mcp_client import get_mcp_tools
from .state import AgentState
from .tools import TOOLS

# ── Model ────────────────────────────────────────────────────────────────────

MODEL = "gpt-5.4-nano"
SYSTEM_PROMPT = "You are a helpful assistant."


# Lazy singleton — OPENAI_API_KEY is read at first call (after dotenv loads).
# MCP tools are available by first call because the FastAPI lifespan starts
# them before the first request arrives.

@lru_cache(maxsize=1)
def _agent_llm():
    all_tools = TOOLS + get_mcp_tools()
    llm = ChatOpenAI(model=MODEL, temperature=0, streaming=True)
    return llm.bind_tools(all_tools) if all_tools else llm


def _all_tools() -> list:
    """Return the full tool list (static + MCP) for runtime lookup."""
    return TOOLS + get_mcp_tools()


# ── Agent ────────────────────────────────────────────────────────────────────

async def agent_node(state: AgentState) -> dict:
    """
    Core ReAct node.  Invokes the LLM with the full message history
    (prepended with the system prompt).

    The LLM either:
      (a) Returns an AIMessage with tool_calls  → graph routes to tools_node
      (b) Returns an AIMessage with text content → graph routes to END

    Because streaming=True, tokens flow through on_chat_model_stream
    events, which the FastAPI endpoint converts to SSE {"token": "..."} frames.
    """
    messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
    response = await _agent_llm().ainvoke(messages)
    return {"messages": [response]}


# ── Tools ────────────────────────────────────────────────────────────────────

async def tools_node(state: AgentState) -> dict:
    """
    Executes every tool call present in the last AIMessage.

    Deduplication rule
    ------------------
    Before executing, the node checks call_log for the (tool, params) pair.
    If it has already been called >= 2 times with the same arguments, the
    call is SKIPPED and a synthetic ToolMessage is returned explaining why.
    This prevents the agent from looping indefinitely on the same tool call.

    After each execution the call_log is updated and retry_count is
    incremented so the graph router can enforce max_retries.
    """
    last: AIMessage = state["messages"][-1]
    if not isinstance(last, AIMessage) or not last.tool_calls:
        return {}

    call_log: list[dict] = list(state.get("call_log", []))
    tool_map = {t.name: t for t in _all_tools()}
    results: list[ToolMessage] = []

    for tc in last.tool_calls:
        tool_name = tc["name"]
        params_key = json.dumps(tc["args"], sort_keys=True)

        entry = next(
            (e for e in call_log
             if e["tool"] == tool_name and e["params"] == params_key),
            None,
        )

        if entry and entry["count"] >= 2:
            results.append(ToolMessage(
                tool_call_id=tc["id"],
                content=(
                    f"[Skipped] '{tool_name}' was already called {entry['count']} "
                    "time(s) with identical arguments. "
                    "Proceeding with the information gathered so far."
                ),
            ))
            continue

        tool = tool_map.get(tool_name)
        output = await tool.ainvoke(tc["args"]) if tool else f"Tool '{tool_name}' not found."
        results.append(ToolMessage(tool_call_id=tc["id"], content=str(output)))

        if entry:
            entry["count"] += 1
        else:
            call_log.append({"tool": tool_name, "params": params_key, "count": 1})

    return {
        "messages": results,
        "call_log": call_log,
        "retry_count": state.get("retry_count", 0) + 1,
    }
