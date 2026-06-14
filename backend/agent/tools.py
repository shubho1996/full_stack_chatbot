"""
Tool registry for the LangGraph agent.

Stage 5  — File System tools (read_file, write_file, list_directory)
            + DuckDuckGo Search tool (free, no API key required).
Stage 6  — Calculator MCP server tools will be appended here.

To register a new tool in a future stage, just append it to TOOLS at the
bottom of this file. The agent node and tools node both import TOOLS, so
no other changes are needed.

── File System Sandbox ───────────────────────────────────────────────────────
All file-system paths are resolved relative to WORKSPACE_DIR and validated
with Path.relative_to() so that traversal sequences like ../../etc/passwd
are caught before any I/O happens.

WORKSPACE_DIR defaults to <project_root>/workspace/ and is created on
startup if it does not exist.  Override with WORKSPACE_DIR in .env.

── DuckDuckGo Search ─────────────────────────────────────────────────────────
Uses the ddgs package directly — free, no API key needed.
Install: pip install ddgs
"""

import os
from pathlib import Path

from ddgs import DDGS
from dotenv import find_dotenv, load_dotenv
from langchain_core.tools import tool

load_dotenv(find_dotenv())

# ── Workspace sandbox ─────────────────────────────────────────────────────────

WORKSPACE_DIR = Path(
    os.getenv("WORKSPACE_DIR") or (Path(__file__).parent.parent.parent / "workspace")
).resolve()

WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


def _safe_path(rel_path: str) -> Path:
    """
    Resolve rel_path inside WORKSPACE_DIR.
    Raises ValueError if the resolved path escapes the sandbox.
    Uses Path.relative_to() which is immune to prefix-collision bugs
    (e.g. /workspace_evil vs /workspace).
    """
    resolved = (WORKSPACE_DIR / rel_path).resolve()
    try:
        resolved.relative_to(WORKSPACE_DIR)
    except ValueError:
        raise ValueError(
            f"Access denied: '{rel_path}' resolves outside the workspace sandbox. "
            "Only paths within the workspace directory are allowed."
        )
    return resolved


# ── File System tools ─────────────────────────────────────────────────────────

@tool
def read_file(path: str) -> str:
    """Read and return the text contents of a file inside the workspace."""
    try:
        return _safe_path(path).read_text(encoding="utf-8")
    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return f"Error: '{path}' does not exist in the workspace."
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def write_file(path: str, content: str) -> str:
    """Write text content to a file in the workspace. Creates parent directories if needed."""
    try:
        p = _safe_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to '{path}'."
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error writing file: {e}"


@tool
def list_directory(path: str = ".") -> str:
    """List the files and subdirectories at a path inside the workspace."""
    try:
        p = _safe_path(path)
        if not p.exists():
            return f"Error: '{path}' does not exist in the workspace."
        if not p.is_dir():
            return f"Error: '{path}' is not a directory."
        entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name))
        if not entries:
            return "(empty directory)"
        return "\n".join(
            f"{'DIR ' if e.is_dir() else 'FILE'} {e.name}" for e in entries
        )
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error listing directory: {e}"


# ── DuckDuckGo Search tool ────────────────────────────────────────────────────

@tool
def duckduckgo_search(query: str) -> str:
    """
    Search the web using DuckDuckGo for up-to-date information.
    Returns the top 5 results with title, URL, and snippet.
    Free — no API key required.
    """
    try:
        results = DDGS().text(query, max_results=5)
        if not results:
            return "No results found."
        return "\n\n".join(
            f"Title: {r.get('title', '')}\n"
            f"URL: {r.get('href', '')}\n"
            f"Snippet: {r.get('body', '')}"
            for r in results
        )
    except Exception as e:
        return f"Error performing DuckDuckGo search: {e}"


# ── Registry ──────────────────────────────────────────────────────────────────
# Imported by nodes.py at startup. All tools listed here are automatically
# bound to the agent LLM and available to the tools_node executor.

TOOLS = [read_file, write_file, list_directory, duckduckgo_search]
