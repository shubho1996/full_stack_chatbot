"""
Tool registry for the LangGraph agent.

Stage 4  — empty (agent responds directly, no tools available).
Stage 5  — File System tools (read_file, write_file, list_directory)
            + Google Search tool will be added here.
Stage 6  — Calculator MCP server tools will be appended here.

To register a tool, append a @tool-decorated function (or a LangChain
BaseTool subclass) to this list.  The agent node and tools node both
import TOOLS, so adding an entry here is all that's needed.
"""

from langchain_core.tools import BaseTool

TOOLS: list[BaseTool] = []
