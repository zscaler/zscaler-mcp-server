"""ZDX deep-trace top processes — agent-first v2 tool.

Mirrors v1's ``zscaler_mcp/tools/zdx/deeptrace_top_processes.py``:

    zdx_list_deeptrace_top_processes
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many
from zscaler_mcp.tools.zdx._common import TraceInput, _as_dicts


class TopProcessSummary(AgentView):
    """Lean view — one top-process group captured during a trace."""

    category: Optional[str] = Field(default=None, description="Process category/bucket.")
    processes: list[dict] = Field(
        default_factory=list, description="Processes in this category (nested rows)."
    )


def _shape_top_process(raw: dict[str, Any]) -> TopProcessSummary:
    procs = pick(raw, "top_processes", "topProcesses", "processes", default=[])
    if not isinstance(procs, list):
        procs = []
    return TopProcessSummary(
        category=pick(raw, "category", "name", "type"),
        processes=procs,
    )


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_troubleshooting",
    input_model=TraceInput,
    output_view=TopProcessSummary,
    is_list=True,
    wire_format=WireFormat.JSON,
)
def zdx_list_deeptrace_top_processes(args: TraceInput) -> list[dict[str, Any]]:
    """List the top processes captured during a ZDX deep trace (curated views).

    Read-only. Returns the process groups captured during the session — useful
    for spotting resource-intensive processes impacting performance.
    """
    if not args.device_id or not args.trace_id:
        raise ValueError("device_id and trace_id are required")
    client = get_zscaler_client(service="zdx")
    result, _, err = client.zdx.troubleshooting.list_top_processes(args.device_id, args.trace_id)
    if err:
        raise RuntimeError(f"Failed to get ZDX deep-trace top processes: {err}")
    return shape_many(_as_dicts(result), _shape_top_process)
