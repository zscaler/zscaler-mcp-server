"""Agent-first ("second step") Zscaler MCP server.

This package is a parallel, incremental evolution of ``zscaler-mcp-server``.
It keeps the Zscaler Python SDK as the transport/auth shim and adds a
response-shaping layer that turns broad SDK objects into narrow, curated,
schema-backed views designed for an AI agent — not for a human reading a
dashboard.

See ``DESIGN.md`` at the repo root for the full rationale.
"""

__version__ = "0.14.0"
