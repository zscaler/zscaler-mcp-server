"""ZDX active applications — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zdx/list_applications.py`` (zdx_list_applications).

``list_apps`` returns a flat list of ActiveApplications models; each is curated
to the identifying id/name plus the ZDX score signal an agent triages on.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many
from zscaler_mcp.tools.zdx._common import scope_query_params

# =============================================================================
# INPUT MODEL
# =============================================================================


class ListApplicationsInput(BaseModel):
    """Inputs for listing active ZDX applications."""

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


class ApplicationSummary(AgentView):
    """Lean view — identify a ZDX application and read its current score."""

    id: str = Field(description="Application ID. Use with `zdx_get_application` etc.")
    name: Optional[str] = Field(default=None, description="Application name.")
    score: Optional[float] = Field(
        default=None, description="Current ZDX score 0-100 (decision-bearing)."
    )
    most_impacted_region: Optional[str] = Field(
        default=None, description="Most-impacted region/location, if reported."
    )
    total_users: Optional[int] = Field(
        default=None, description="Total users observed for this app (relational signal)."
    )


def _shape_app(raw: dict[str, Any]) -> ApplicationSummary:
    return ApplicationSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name"),
        score=pick(raw, "score"),
        most_impacted_region=pick(raw, "most_impacted_region", "mostImpactedRegion"),
        total_users=pick(raw, "total_users", "totalUsers"),
    )


# =============================================================================
# TOOL
# =============================================================================


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_reports",
    input_model=ListApplicationsInput,
    output_view=ApplicationSummary,
    is_list=True,
)
def zdx_list_applications(args: ListApplicationsInput) -> list[dict[str, Any]]:
    """List active ZDX applications as curated, agent-facing views.

    Read-only. Returns one row per application (id, name, ZDX score, impact
    signals). Filter by location/department/geo and the `since` HOURS window.
    Use a returned `id` with `zdx_get_application`, `zdx_get_application_metric`,
    or `zdx_list_application_users`.
    """
    client = get_zscaler_client(service="zdx")

    qp = scope_query_params(
        location_id=args.location_id,
        department_id=args.department_id,
        geo_id=args.geo_id,
        since=args.since,
    )

    results, _, err = client.zdx.apps.list_apps(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZDX applications: {err}")

    return shape_many([app.as_dict() for app in (results or [])], _shape_app)
