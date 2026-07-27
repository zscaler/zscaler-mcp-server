"""ZDX deep-trace listing — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zdx/list_deep_traces.py``:

    zdx_list_device_deep_traces, zdx_get_device_deep_trace

Returns lean deep-trace identity rows (id, status, session name, app, ISO
timestamps). The metric/event readers live in the per-metric modules.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many, shape_one
from zscaler_mcp.tools.zdx._common import TraceInput

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListDeviceTracesInput(BaseModel):
    """Inputs for listing deep traces on a device."""

    device_id: Annotated[str, Field(description="ZDX device ID (string, even if numeric).")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_troubleshooting",
    input_model=ListDeviceTracesInput,
    is_list=True,
)
def zdx_list_device_deep_traces(args: ListDeviceTracesInput) -> list[dict[str, Any]]:
    """List deep-trace sessions for a ZDX device (full records).

    Read-only. Returns one row per trace (id, status, session name, app, ISO
    timestamps). Use a returned `trace_id` with the deep-trace metric/event tools
    or `zdx_get_device_deep_trace`.
    """
    if not args.device_id:
        raise ValueError("device_id is required")
    client = get_zscaler_client(service="zdx")
    result, _, err = client.zdx.troubleshooting.list_deeptraces(args.device_id)
    if err:
        raise RuntimeError(f"Failed to list ZDX deep traces: {err}")

    rows: list[dict[str, Any]] = []
    for wrapper in result or []:
        traces = getattr(wrapper, "traces", None)
        if traces:
            rows.extend(t.as_dict() for t in traces)
        elif hasattr(wrapper, "as_dict"):
            rows.append(wrapper.as_dict())
    return shape_many(rows)


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_troubleshooting",
    input_model=TraceInput,
    is_list=False,
)
def zdx_get_device_deep_trace(args: TraceInput) -> dict[str, Any]:
    """Get one ZDX deep-trace session.

    Read-only. The SDK returns a single-element list; the trace record is
    unwrapped, timestamps ISO-normalized, and shaped to the identity fields.
    """
    if not args.device_id or not args.trace_id:
        raise ValueError("device_id and trace_id are required")
    client = get_zscaler_client(service="zdx")
    result, _, err = client.zdx.troubleshooting.get_deeptrace(args.device_id, args.trace_id)
    if err:
        raise RuntimeError(f"Failed to get ZDX deep trace {args.trace_id}: {err}")
    raw = result[0].as_dict() if result and len(result) > 0 else {}
    return shape_one(raw)
