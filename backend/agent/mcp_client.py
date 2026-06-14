"""
MCP client lifecycle manager — Stage 6

Discovers tools from the calculator MCP server at startup and stores them
as LangChain tools in _mcp_tools.  langchain-mcp-adapters 0.1.0+ manages
its own subprocess lifecycle per-call, so no persistent process is kept.

Usage (in main.py lifespan):
    from agent.mcp_client import start_mcp_client, stop_mcp_client

Other modules call get_mcp_tools() to access the loaded tools.
"""

import logging
import sys
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

_mcp_tools: list = []

_CALCULATOR_SERVER = (
    Path(__file__).parent.parent.parent / "mcp_servers" / "calculator" / "server.py"
).resolve()


def get_mcp_tools() -> list:
    """Return the list of LangChain tools discovered from all MCP servers."""
    return _mcp_tools


async def start_mcp_client() -> None:
    """Discover MCP tools at startup and cache them in _mcp_tools."""
    global _mcp_tools

    if not _CALCULATOR_SERVER.exists():
        logger.warning("Calculator MCP server not found at %s — skipping.", _CALCULATOR_SERVER)
        return

    try:
        client = MultiServerMCPClient({
            "calculator": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(_CALCULATOR_SERVER)],
            }
        })
        _mcp_tools = await client.get_tools()
        logger.info("MCP calculator tools loaded: %s", [t.name for t in _mcp_tools])
    except Exception:
        logger.exception("Failed to load MCP tools — calculator tools unavailable.")
        _mcp_tools = []


async def stop_mcp_client() -> None:
    """Placeholder — no persistent subprocess to clean up in this adapter version."""
    global _mcp_tools
    _mcp_tools = []
