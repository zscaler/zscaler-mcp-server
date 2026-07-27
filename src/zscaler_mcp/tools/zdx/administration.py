"""ZDX administration (departments + locations) — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zdx/administration.py``
(zdx_list_departments, zdx_list_locations).

Both endpoints return a flat list of SDK models; each is curated to the
identifying id/name pair an agent needs to scope subsequent ZDX queries.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListAdminInput(BaseModel):
    """Inputs shared by the ZDX department / location list tools."""

    search: Annotated[
        Optional[str],
        Field(default=None, description="Substring match on the resource name or ID."),
    ] = None
    since: Annotated[
        Optional[int],
        Field(default=None, ge=1, description="Look-back window in HOURS (ZDX default 2h)."),
    ] = None


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_reports",
    input_model=ListAdminInput,
    is_list=True,
)
def zdx_list_departments(args: ListAdminInput) -> list[dict[str, Any]]:
    """List ZDX departments as curated id/name rows.

    Read-only. Use a returned `id` as the `department_id` scope filter on other
    ZDX tools. `since` is in HOURS (default 2h).
    """
    client = get_zscaler_client(service="zdx")

    qp: dict[str, Any] = {}
    if args.search:
        qp["search"] = args.search
    if args.since is not None:
        qp["since"] = args.since

    departments, _, err = client.zdx.admin.list_departments(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZDX departments: {err}")

    return shape_many([d.as_dict() for d in (departments or [])])


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_reports",
    input_model=ListAdminInput,
    is_list=True,
)
def zdx_list_locations(args: ListAdminInput) -> list[dict[str, Any]]:
    """List ZDX locations as curated id/name rows.

    Read-only. Use a returned `id` as the `location_id` scope filter on other
    ZDX tools. `since` is in HOURS (default 2h).
    """
    client = get_zscaler_client(service="zdx")

    qp: dict[str, Any] = {}
    if args.search:
        qp["search"] = args.search
    if args.since is not None:
        qp["since"] = args.since

    locations, _, err = client.zdx.admin.list_locations(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZDX locations: {err}")

    return shape_many([loc.as_dict() for loc in (locations or [])])
