"""ZDX deep-trace top processes — agent-first v2 tool.

Mirrors v1's ``zscaler_mcp/tools/zdx/deeptrace_top_processes.py``:

    zdx_list_deeptrace_top_processes
"""

from __future__ import annotations

from typing import Any

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zdx._common import TraceInput, _as_dicts


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_troubleshooting",
    input_model=TraceInput,
    is_list=True,
    wire_format=WireFormat.JSON,
    # Process names are authored by whoever wrote the software running on the
    # traced endpoint — the same publisher-authored string class as the software
    # inventory (and for malware, an adversary-chosen string). Flagged in the
    # same audit so this class stops surfacing one scan at a time.
    untrusted_content=True,
    untrusted_content_note=(
        "These are reliable trace captures from an enrolled device — report them "
        "faithfully — but process names are authored by whoever wrote the software "
        "running on the endpoint, not by this tenant's users or admins."
    ),
)
def zdx_list_deeptrace_top_processes(args: TraceInput) -> list[dict[str, Any]]:
    """List the top processes captured during a ZDX deep trace (full records).

    Read-only. Returns the process groups captured during the session — useful
    for spotting resource-intensive processes impacting performance.
    """
    if not args.device_id or not args.trace_id:
        raise ValueError("device_id and trace_id are required")
    client = get_zscaler_client(service="zdx")
    result, _, err = client.zdx.troubleshooting.list_top_processes(args.device_id, args.trace_id)
    if err:
        raise RuntimeError(f"Failed to get ZDX deep-trace top processes: {err}")
    return shape_many(_as_dicts(result))
