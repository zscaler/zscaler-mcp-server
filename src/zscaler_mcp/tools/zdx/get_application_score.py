"""ZDX application score + score trend — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zdx/get_application_score.py``
(zdx_get_application, zdx_get_application_score_trend).

Both endpoints return ``[obj]`` (single-element list). The score response carries
nested most-impacted-region detail and the trend carries a datapoint time-series,
so both views keep the nested payload and the tools force JSON on the wire.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, coalesce, pick
from zscaler_mcp.tools.zdx._common import scope_query_params

# =============================================================================
# INPUT MODEL
# =============================================================================


class AppScopeInput(BaseModel):
    """Inputs shared by the ZDX application score / trend tools."""

    app_id: Annotated[str, Field(description="Application ID (string, even if numeric).")]
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
# OUTPUT VIEWS
# =============================================================================


class ApplicationScore(AgentView):
    """ZDX score for an application, with the most-impacted-region breakdown.

    The headline `score` is the decision-bearing field; `most_impacted_regions`
    is the nested breakdown the admin asked for and is preserved as-is.
    """

    id: str = Field(description="Application ID.")
    name: Optional[str] = Field(default=None, description="Application name.")
    score: Optional[float] = Field(default=None, description="Current ZDX score (0-100).")
    most_impacted_regions: list[dict] = Field(
        default_factory=list,
        description="Per-region impact breakdown (nested time-series/geo detail).",
    )
    stats: Optional[dict] = Field(
        default=None, description="Aggregate score stats, if reported (nested)."
    )


class ApplicationScoreTrend(AgentView):
    """ZDX score trend for an application — the datapoint time-series.

    The `datapoints` array is the trend the admin asked for and is preserved.
    """

    id: str = Field(description="Application ID.")
    metric: Optional[str] = Field(default=None, description="Trend metric name, if reported.")
    unit: Optional[str] = Field(default=None, description="Trend value unit, if reported.")
    datapoints: list[dict] = Field(
        default_factory=list, description="Score-over-time datapoints (nested time-series)."
    )


def _shape_score(raw: dict[str, Any]) -> ApplicationScore:
    return ApplicationScore(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name"),
        score=pick(raw, "score"),
        most_impacted_regions=coalesce(
            raw, "most_impacted_regions", "mostImpactedRegions", "most_impacted_region"
        ),
        stats=pick(raw, "stats"),
    )


def _shape_trend(raw: dict[str, Any]) -> ApplicationScoreTrend:
    return ApplicationScoreTrend(
        id=str(pick(raw, "id", default="")),
        metric=pick(raw, "metric"),
        unit=pick(raw, "unit"),
        datapoints=coalesce(raw, "datapoints", "data_points"),
    )


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_reports",
    input_model=AppScopeInput,
    output_view=ApplicationScore,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zdx_get_application(args: AppScopeInput) -> dict[str, Any]:
    """Get the ZDX score for one application, with its most-impacted regions.

    Read-only. Returns the headline ZDX score plus the per-region impact
    breakdown for the `since` HOURS window (default 2h). Use `app_id` from
    `zdx_list_applications`.
    """
    if not args.app_id:
        raise ValueError("app_id is required")

    client = get_zscaler_client(service="zdx")
    qp = scope_query_params(
        location_id=args.location_id,
        department_id=args.department_id,
        geo_id=args.geo_id,
        since=args.since,
    )

    result, _, err = client.zdx.apps.get_app(args.app_id, query_params=qp)
    if err:
        raise RuntimeError(f"Failed to get ZDX application score for {args.app_id}: {err}")

    if result and len(result) > 0:
        return _shape_score(result[0].as_dict()).model_dump()
    return _shape_score({}).model_dump()


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_reports",
    input_model=AppScopeInput,
    output_view=ApplicationScoreTrend,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zdx_get_application_score_trend(args: AppScopeInput) -> dict[str, Any]:
    """Get the ZDX score trend (over time) for one application.

    Read-only. Returns the score-over-time datapoints for the `since` HOURS
    window (default 2h) so the agent can reason about whether an app's
    experience is improving or degrading. Use `app_id` from
    `zdx_list_applications`.
    """
    if not args.app_id:
        raise ValueError("app_id is required")

    client = get_zscaler_client(service="zdx")
    qp = scope_query_params(
        location_id=args.location_id,
        department_id=args.department_id,
        geo_id=args.geo_id,
        since=args.since,
    )

    result, _, err = client.zdx.apps.get_app_score(args.app_id, query_params=qp)
    if err:
        raise RuntimeError(f"Failed to get ZDX application score trend for {args.app_id}: {err}")

    if result and len(result) > 0:
        return _shape_trend(result[0].as_dict()).model_dump()
    return _shape_trend({}).model_dump()
