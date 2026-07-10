"""ZDX deep-trace cloud-path metrics — agent-first v2 tool.

Mirrors v1's ``zscaler_mcp/tools/zdx/deeptrace_cloudpath_metrics.py``:

    zdx_get_deeptrace_cloudpath_metrics
"""

from __future__ import annotations

from zscaler_mcp.tools.zdx._common import build_metric_tool

zdx_get_deeptrace_cloudpath_metrics = build_metric_tool(
    "get_deeptrace_cloudpath_metrics",
    "deep-trace cloud-path metrics",
    name="zdx_get_deeptrace_cloudpath_metrics",
    description=(
        "Get cloud-path metrics captured during a ZDX deep trace (curated, nested "
        "time-series JSON). Read-only."
    ),
)
