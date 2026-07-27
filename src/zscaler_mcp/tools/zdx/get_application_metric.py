"""ZDX application metrics — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zdx/get_application_metric.py``
(zdx_get_application_metric).

``get_app_metrics`` returns a list of ApplicationMetrics models, each carrying a
nested datapoint time-series (Page Fetch Time / DNS / availability). The view
keeps the metric identity plus the nested datapoints, and the tool forces JSON.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zdx._common import scope_query_params

# =============================================================================
# INPUT MODEL
# =============================================================================


class GetApplicationMetricInput(BaseModel):
    """Inputs for retrieving ZDX metrics for an application."""

    app_id: Annotated[str, Field(description="Application ID (string, even if numeric).")]
    metric_name: Annotated[
        Optional[Literal["pft", "dns", "availability"]],
        Field(
            default=None,
            description=(
                "Metric to return: 'pft' (Page Fetch Time), 'dns' (DNS Time), or "
                "'availability'. Omit for all metrics."
            ),
        ),
    ] = None
    location_id: Annotated[
        Optional[list[str]], Field(default=None, description="Filter by location ID(s).")
    ] = None
    department_id: Annotated[
        Optional[list[str]], Field(default=None, description="Filter by department ID(s).")
    ] = None
    geo_id: Annotated[
        Optional[list[str]], Field(default=None, description="Filter by geolocation ID(s).")
    ] = None
    since: Annotated[
        Optional[int],
        Field(default=None, ge=1, description="Look-back window in HOURS (ZDX default 2h)."),
    ] = None


# =============================================================================
# OUTPUT VIEW
# =============================================================================


# =============================================================================
# TOOL
# =============================================================================


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_reports",
    input_model=GetApplicationMetricInput,
    is_list=True,
    wire_format=WireFormat.JSON,
)
def zdx_get_application_metric(args: GetApplicationMetricInput) -> list[dict[str, Any]]:
    """Get ZDX performance metrics for one application (time-series).

    Read-only. Returns one series per metric (Page Fetch Time, DNS Time,
    availability), each with its datapoints over the `since` HOURS window
    (default 2h). Pass `metric_name` to narrow to a single metric. Use `app_id`
    from `zdx_list_applications`.
    """
    if not args.app_id:
        raise ValueError("app_id is required")

    client = get_zscaler_client(service="zdx")
    qp = scope_query_params(
        location_id=args.location_id,
        department_id=args.department_id,
        geo_id=args.geo_id,
        since=args.since,
        metric_name=args.metric_name,
    )

    results, _, err = client.zdx.apps.get_app_metrics(args.app_id, query_params=qp)
    if err:
        raise RuntimeError(f"Failed to get ZDX application metrics for {args.app_id}: {err}")

    return shape_many([m.as_dict() for m in (results or [])])
