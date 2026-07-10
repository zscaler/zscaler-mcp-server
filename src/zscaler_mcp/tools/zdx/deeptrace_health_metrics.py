"""ZDX deep-trace health metrics — agent-first v2 tool.

Mirrors v1's ``zscaler_mcp/tools/zdx/deeptrace_health_metrics.py``:

    zdx_get_deeptrace_health_metrics
"""

from __future__ import annotations

from zscaler_mcp.tools.zdx._common import build_metric_tool

zdx_get_deeptrace_health_metrics = build_metric_tool(
    "get_deeptrace_health_metrics",
    "deep-trace health metrics",
    name="zdx_get_deeptrace_health_metrics",
    description=(
        "Get device health metrics captured during a ZDX deep trace (curated, "
        "nested time-series JSON). Read-only."
    ),
)
