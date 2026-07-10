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
from zscaler_mcp.shaping import AgentView, pick, shape_many
from zscaler_mcp.tools.zdx._common import TraceInput, convert_timestamps

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListDeviceTracesInput(BaseModel):
    """Inputs for listing deep traces on a device."""

    device_id: Annotated[str, Field(description="ZDX device ID (string, even if numeric).")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class DeepTraceSummary(AgentView):
    """Lean view — one deep-trace session row."""

    trace_id: str = Field(description="Trace ID. Use with the deep-trace metric/event tools.")
    status: Optional[str] = Field(default=None, description="Trace session status.")
    session_name: Optional[str] = Field(default=None, description="Session name.")
    app_id: Optional[str] = Field(default=None, description="Application ID being traced.")
    created: Optional[str] = Field(default=None, description="Creation time (ISO).")
    started: Optional[str] = Field(default=None, description="Start time (ISO).")
    ended: Optional[str] = Field(default=None, description="End time (ISO).")


# =============================================================================
# SHAPERS
# =============================================================================


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _shape_trace(raw: dict[str, Any]) -> DeepTraceSummary:
    converted = convert_timestamps(raw)
    return DeepTraceSummary(
        trace_id=str(pick(converted, "trace_id", "traceId", "id", default="")),
        status=pick(converted, "status", "state"),
        session_name=pick(converted, "session_name", "sessionName", "name"),
        app_id=_opt_str(pick(converted, "app_id", "appId")),
        created=_opt_str(pick(converted, "created")),
        started=_opt_str(pick(converted, "started")),
        ended=_opt_str(pick(converted, "ended")),
    )


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_troubleshooting",
    input_model=ListDeviceTracesInput,
    output_view=DeepTraceSummary,
    is_list=True,
)
def zdx_list_device_deep_traces(args: ListDeviceTracesInput) -> list[dict[str, Any]]:
    """List deep-trace sessions for a ZDX device (curated views).

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
    return shape_many(rows, _shape_trace)


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_troubleshooting",
    input_model=TraceInput,
    output_view=DeepTraceSummary,
    is_list=False,
)
def zdx_get_device_deep_trace(args: TraceInput) -> dict[str, Any]:
    """Get one ZDX deep-trace session as a curated view.

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
    return _shape_trace(raw).model_dump()
