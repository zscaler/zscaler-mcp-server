"""Tool registration package — declarative, co-located, self-registering.

Unlike v1's central ``services.py`` catalog (a hand-maintained list of dicts),
v2 tools declare themselves at their own definition site via the ``@tool``
decorator and register into a central :class:`Registry` at import time. The
filtering layer (toolsets / write allowlist / disabled patterns) is a
:meth:`Registry.select` query over those records.

This ``__init__`` only declares the package's public API. Implementations live
in :mod:`~zscaler_mcp.registry.spec`, :mod:`~zscaler_mcp.registry.registry`,
:mod:`~zscaler_mcp.registry.decorator`, and :mod:`~zscaler_mcp.registry.discovery`.

    from zscaler_mcp.registry import tool, READ, REGISTRY, discover_tools
"""

from zscaler_mcp.registry.decorator import tool
from zscaler_mcp.registry.discovery import discover_tools
from zscaler_mcp.registry.fastmcp_bridge import build_function_tool
from zscaler_mcp.registry.registry import REGISTRY, Registry
from zscaler_mcp.registry.spec import CREATE, DELETE, READ, UPDATE, ToolSpec

__all__ = [
    "tool",
    "discover_tools",
    "build_function_tool",
    "REGISTRY",
    "Registry",
    "ToolSpec",
    "READ",
    "CREATE",
    "UPDATE",
    "DELETE",
]
