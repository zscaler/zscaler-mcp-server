"""ZDX score-analysis — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zdx/deeptrace_analysis.py``:

    zdx_start_analysis   (CREATE)
    zdx_get_analysis     (READ)
    zdx_delete_analysis  (DELETE — HMAC-confirmed)

A score analysis evaluates connectivity/performance for a device+app over an
optional epoch range. The write tools are gated behind ``--write-tools``; the
delete is additionally HMAC-confirmed by the server bridge before the body runs.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import CREATE, DELETE, READ, tool
from zscaler_mcp.shaping import AgentView, pick
from zscaler_mcp.tools.zdx._common import _as_dicts, convert_timestamps

# =============================================================================
# INPUT MODELS
# =============================================================================


class GetAnalysisInput(BaseModel):
    """Inputs for getting a ZDX score-analysis status/result."""

    analysis_id: Annotated[str, Field(description="Analysis ID (string, even if numeric).")]


class StartAnalysisInput(BaseModel):
    """Inputs for starting a ZDX score analysis."""

    device_id: Annotated[str, Field(description="ZDX device ID (string, even if numeric).")]
    app_id: Annotated[
        int, Field(description="Application ID as an INTEGER (from zdx_list_applications).")
    ]
    t0: Annotated[
        Optional[int], Field(default=None, description="Start time as Unix epoch timestamp.")
    ] = None
    t1: Annotated[
        Optional[int], Field(default=None, description="End time as Unix epoch timestamp.")
    ] = None


class DeleteAnalysisInput(BaseModel):
    """Inputs for stopping/deleting a ZDX score analysis (destructive)."""

    analysis_id: Annotated[str, Field(description="Analysis ID to stop/delete.")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class AnalysisStatus(AgentView):
    """Lean view — a ZDX score-analysis status row."""

    analysis_id: Optional[str] = Field(default=None, description="Analysis ID.")
    status: Optional[str] = Field(default=None, description="Analysis status (running/complete).")
    data: dict = Field(default_factory=dict, description="Analysis result payload, if complete.")


class StartedAnalysis(AgentView):
    """Result of starting a score analysis — the new analysis identity."""

    analysis_id: Optional[str] = Field(default=None, description="New analysis ID.")
    status: Optional[str] = Field(default=None, description="Analysis status.")


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
    action=READ,
    service="zdx",
    toolset="zdx_troubleshooting",
    input_model=GetAnalysisInput,
    output_view=AnalysisStatus,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zdx_get_analysis(args: GetAnalysisInput) -> dict[str, Any]:
    """Get the status/result of a ZDX score analysis (full record).

    Read-only. Returns whether the analysis is still running or its results if
    complete. Start one with `zdx_start_analysis`.
    """
    if not args.analysis_id:
        raise ValueError("analysis_id is required")
    client = get_zscaler_client(service="zdx")
    result, _, err = client.zdx.troubleshooting.get_analysis(args.analysis_id)
    if err:
        raise RuntimeError(f"Failed to get ZDX analysis {args.analysis_id}: {err}")

    rows = _as_dicts(result)
    first = rows[0] if rows else {}
    if not isinstance(first, dict):
        first = {}
    return AnalysisStatus(
        analysis_id=args.analysis_id,
        status=pick(first, "status", "state"),
        data=convert_timestamps(first) if first else {},
    ).model_dump()


@tool(
    action=CREATE,
    service="zdx",
    toolset="zdx_troubleshooting",
    input_model=StartAnalysisInput,
    output_view=StartedAnalysis,
    is_list=False,
)
def zdx_start_analysis(args: StartAnalysisInput) -> dict[str, Any]:
    """Start a ZDX score analysis on a device/app (write).

    Evaluates connectivity and performance metrics over the optional
    `t0`/`t1` epoch range. Gated by HMAC write-confirmation and `--write-tools`.
    """
    client = get_zscaler_client(service="zdx")
    sdk_kwargs: dict[str, Any] = {"device_id": args.device_id, "app_id": int(args.app_id)}
    if args.t0 is not None:
        sdk_kwargs["t0"] = args.t0
    if args.t1 is not None:
        sdk_kwargs["t1"] = args.t1
    result, _, err = client.zdx.troubleshooting.start_analysis(**sdk_kwargs)
    if err:
        raise RuntimeError(f"Failed to start ZDX analysis: {err}")

    raw = result.as_dict() if result and hasattr(result, "as_dict") else {}
    return StartedAnalysis(
        analysis_id=_opt_str(pick(raw, "analysis_id", "analysisId", "id")),
        status=pick(raw, "status", "state") or "started",
    ).model_dump()


@tool(
    action=DELETE,
    service="zdx",
    toolset="zdx_troubleshooting",
    input_model=DeleteAnalysisInput,
    output_view=OperationResult,
    is_list=False,
)
def zdx_delete_analysis(args: DeleteAnalysisInput) -> dict[str, Any]:
    """Stop/delete a running ZDX score analysis (destructive write).

    Cannot be undone. Gated by HMAC write-confirmation and `--write-tools`.
    """
    if not args.analysis_id:
        raise ValueError("analysis_id is required for delete")
    client = get_zscaler_client(service="zdx")
    _, _, err = client.zdx.troubleshooting.delete_analysis(args.analysis_id)
    if err:
        raise RuntimeError(f"Failed to delete ZDX analysis {args.analysis_id}: {err}")
    return OperationResult(
        success=True,
        message=f"Stopped/deleted analysis {args.analysis_id}.",
    ).model_dump()
