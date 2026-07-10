"""ZDX deep-trace web-probe metrics — agent-first v2 tool.

Mirrors v1's ``zscaler_mcp/tools/zdx/deeptrace_webprobe_metrics.py``:

    zdx_get_deeptrace_webprobe_metrics
"""

from __future__ import annotations

from zscaler_mcp.tools.zdx._common import build_metric_tool

zdx_get_deeptrace_webprobe_metrics = build_metric_tool(
    "get_deeptrace_webprobe_metrics",
    "deep-trace web-probe metrics",
    name="zdx_get_deeptrace_webprobe_metrics",
    description=(
        "Get web-probe metrics captured during a ZDX deep trace (curated, nested "
        "time-series JSON). Read-only."
    ),
)
