"""ZDX deep-trace management (start / delete) — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zdx/deeptrace_manage.py``:

    zdx_start_deeptrace   (CREATE)
    zdx_delete_deeptrace  (DELETE — HMAC-confirmed)

These are the write half of the read-heavy ZDX troubleshooting surface. HMAC
write confirmation is enforced by the server bridge BEFORE the tool body runs;
the body just performs the SDK mutation and shapes the result. Write tools are
disabled unless the operator passes ``--write-tools``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import CREATE, DELETE, tool
from zscaler_mcp.shaping import AgentView, pick

# =============================================================================
# INPUT MODELS
# =============================================================================


class StartDeepTraceInput(BaseModel):
    """Inputs for starting a ZDX deep-trace session.

    Workflow: `zdx_list_applications` → `app_id`; then
    `zdx_get_web_probes(device_id, app_id)` → `web_probe_id`; and
    `zdx_list_cloudpath_probes(device_id, app_id)` → `cloudpath_probe_id`.
    """

    device_id: Annotated[str, Field(description="ZDX device ID (string, even if numeric).")]
    session_name: Annotated[str, Field(description="Name for the deep-trace session.")]
    app_id: Annotated[
        int, Field(description="Application ID as an INTEGER (from zdx_list_applications).")
    ]
    web_probe_id: Annotated[
        int, Field(description="Web probe ID as an INTEGER (from zdx_get_web_probes).")
    ]
    cloudpath_probe_id: Annotated[
        int,
        Field(description="Cloud-path probe ID as an INTEGER (from zdx_list_cloudpath_probes)."),
    ]
    session_length_minutes: Annotated[
        int,
        Field(default=5, description="Session duration in minutes. Supported: 5, 15, 30, 60."),
    ] = 5
    probe_device: Annotated[
        bool,
        Field(default=True, description="Probe the device for CPU/memory/disk/network metrics."),
    ] = True


class DeleteDeepTraceInput(BaseModel):
    """Inputs for deleting a ZDX deep-trace session (destructive)."""

    device_id: Annotated[str, Field(description="ZDX device ID (string, even if numeric).")]
    trace_id: Annotated[str, Field(description="Deep-trace session ID to delete.")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class StartedTrace(AgentView):
    """Result of starting a deep trace — the new trace identity."""

    trace_id: Optional[str] = Field(default=None, description="New deep-trace session ID.")
    status: Optional[str] = Field(default=None, description="Session status.")
    session_name: Optional[str] = Field(default=None, description="Session name (echoed).")


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=CREATE,
    service="zdx",
    toolset="zdx_troubleshooting",
    input_model=StartDeepTraceInput,
    output_view=StartedTrace,
    is_list=False,
)
def zdx_start_deeptrace(args: StartDeepTraceInput) -> dict[str, Any]:
    """Start a ZDX deep-trace session (write).

    Captures network path, web-probe, health, and event data for
    troubleshooting. Gated by HMAC write-confirmation and `--write-tools`.
    Resolve `app_id` / `web_probe_id` / `cloudpath_probe_id` via
    `zdx_list_applications`, `zdx_get_web_probes`, `zdx_list_cloudpath_probes`
    first (all INTEGERS).
    """
    client = get_zscaler_client(service="zdx")
    sdk_kwargs = {
        "session_name": args.session_name,
        "app_id": int(args.app_id),
        "web_probe_id": int(args.web_probe_id),
        "cloudpath_probe_id": int(args.cloudpath_probe_id),
        "session_length_minutes": args.session_length_minutes,
        "probe_device": args.probe_device,
    }
    result, _, err = client.zdx.troubleshooting.start_deeptrace(args.device_id, **sdk_kwargs)
    if err:
        raise RuntimeError(f"Failed to start ZDX deep trace: {err}")

    raw = result.as_dict() if result and hasattr(result, "as_dict") else {}
    return StartedTrace(
        trace_id=_opt_str(pick(raw, "trace_id", "traceId", "id")),
        status=pick(raw, "status", "state") or "started",
        session_name=args.session_name,
    ).model_dump()


@tool(
    action=DELETE,
    service="zdx",
    toolset="zdx_troubleshooting",
    input_model=DeleteDeepTraceInput,
    output_view=OperationResult,
    is_list=False,
)
def zdx_delete_deeptrace(args: DeleteDeepTraceInput) -> dict[str, Any]:
    """Delete a ZDX deep-trace session (destructive write).

    Cannot be undone. Gated by HMAC write-confirmation and `--write-tools`.
    """
    if not args.device_id or not args.trace_id:
        raise ValueError("device_id and trace_id are required for delete")
    client = get_zscaler_client(service="zdx")
    _, _, err = client.zdx.troubleshooting.delete_deeptrace(args.device_id, args.trace_id)
    if err:
        raise RuntimeError(f"Failed to delete ZDX deep trace {args.trace_id}: {err}")
    return OperationResult(
        success=True,
        message=f"Deleted deep trace {args.trace_id} for device {args.device_id}.",
    ).model_dump()
