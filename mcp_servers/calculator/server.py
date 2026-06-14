"""
Calculator MCP Server — Stage 6

Exposes five arithmetic tools over stdio transport:
  add, subtract, multiply, divide, evaluate

Run standalone:
    python mcp_servers/calculator/server.py

The backend starts this as a subprocess via langchain-mcp-adapters.
"""

import ast
import operator as _op

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Calculator")

# ── Basic arithmetic ──────────────────────────────────────────────────────────

@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers and return the result."""
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract b from a and return the result."""
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return the result."""
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """
    Divide a by b and return the result.
    Raises an error if b is zero.
    """
    if b == 0:
        raise ValueError("Division by zero is undefined.")
    return a / b


# ── Safe expression evaluator ─────────────────────────────────────────────────

_BINARY_OPS = {
    ast.Add:      _op.add,
    ast.Sub:      _op.sub,
    ast.Mult:     _op.mul,
    ast.Div:      _op.truediv,
    ast.FloorDiv: _op.floordiv,
    ast.Pow:      _op.pow,
    ast.Mod:      _op.mod,
}

_UNARY_OPS = {
    ast.USub: _op.neg,
    ast.UAdd: _op.pos,
}


def _eval_node(node: ast.AST) -> float:
    """Recursively evaluate a safe arithmetic AST node."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError(f"Unsupported literal: {node.value!r}")

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        fn = _BINARY_OPS.get(type(node.op))
        if fn is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        if isinstance(node.op, ast.Div) and right == 0:
            raise ValueError("Division by zero is undefined.")
        return fn(left, right)

    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand)
        fn = _UNARY_OPS.get(type(node.op))
        if fn is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return fn(operand)

    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


@mcp.tool()
def evaluate(expression: str) -> float:
    """
    Safely evaluate a mathematical expression string and return the result.
    Supports: +, -, *, /, //, **, % and parentheses.
    No exec or eval — uses AST parsing only.

    Example: evaluate("2 ** 10 + 5 * 3") → 1039.0
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Invalid expression syntax: {e}")

    return _eval_node(tree.body)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
