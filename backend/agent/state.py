"""
AgentState — the single source of truth passed between every node in the graph.

Fields
------
messages      Full conversation history. The add_messages reducer appends
              new messages rather than overwriting, so each node just returns
              the new messages it wants to add.

max_retries   Maximum number of tool-execution rounds per turn (default 5).
              The agent-tools loop runs at most this many times.

retry_count   Incremented by the tools node on every tool-execution round.
              When retry_count >= max_retries the router sends the agent
              straight to END regardless of pending tool calls.

call_log      Deduplication ledger.  Each entry is:
                  {"tool": str, "params": str (JSON), "count": int}
              The tools node checks this before executing any tool call.
              If the same (tool, params) pair has been called >= 2 times
              the call is skipped and a synthetic ToolMessage is returned.
"""

from typing import Annotated, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    max_retries: int
    retry_count: int
    call_log: list[dict]
