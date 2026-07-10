"""ZDX deep-trace events — agent-first v2 tool.

Mirrors v1's ``zscaler_mcp/tools/zdx/deeptrace_events.py``:

    zdx_get_deeptrace_events
"""

from __future__ import annotations

from zscaler_mcp.tools.zdx._common import build_metric_tool

zdx_get_deeptrace_events = build_metric_tool(
    "get_deeptrace_events",
    "deep-trace events",
    name="zdx_get_deeptrace_events",
    description=(
        "Get the events captured during a ZDX deep trace (curated, nested JSON "
        "with ISO timestamps). Read-only."
    ),
)
