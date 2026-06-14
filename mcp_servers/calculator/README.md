# Calculator MCP Server

A simple MCP server that exposes arithmetic tools over `stdio` transport.
Built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk) (bundled in the `mcp` SDK).

## Tools

| Tool | Signature | Description |
|---|---|---|
| `add` | `(a: float, b: float) → float` | Addition |
| `subtract` | `(a: float, b: float) → float` | Subtraction |
| `multiply` | `(a: float, b: float) → float` | Multiplication |
| `divide` | `(a: float, b: float) → float` | Division — raises error on divide-by-zero |
| `evaluate` | `(expression: str) → float` | Safe expression evaluator (AST only, no `exec`) |

## Requirements

```bash
pip install mcp
```

## Running standalone

```bash
python mcp_servers/calculator/server.py
```

The server listens on `stdio`. To test it interactively, use the MCP inspector:

```bash
npx @modelcontextprotocol/inspector python mcp_servers/calculator/server.py
```

## evaluate — Supported syntax

Operators: `+`, `-`, `*`, `/`, `//`, `**`, `%` and parentheses.

```
evaluate("2 ** 10 + 5 * 3")   → 1039.0
evaluate("(100 / 4) + 37")    →   62.0
evaluate("17 % 5")            →    2.0
```

Variables, function calls, and any non-numeric literals are rejected.

## Integration

The backend starts this server as a subprocess at startup via
`langchain-mcp-adapters` (`MultiServerMCPClient`). No manual startup required
when running the backend.
