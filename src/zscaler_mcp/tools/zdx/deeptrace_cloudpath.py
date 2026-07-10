"""ZDX deep-trace cloud path — agent-first v2 tool.

Mirrors v1's ``zscaler_mcp/tools/zdx/deeptrace_cloudpath.py``:

    zdx_get_deeptrace_cloudpath
"""

from __future__ import annotations

from zscaler_mcp.tools.zdx._common import build_metric_tool

zdx_get_deeptrace_cloudpath = build_metric_tool(
    "get_deeptrace_cloudpath",
    "deep-trace cloud path",
    name="zdx_get_deeptrace_cloudpath",
    description=(
        "Get the cloud-path (hop-by-hop network path) captured during a ZDX deep "
        "trace (curated, nested JSON). Read-only."
    ),
)
