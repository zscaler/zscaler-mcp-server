"""ZDX ongoing alerts — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zdx/list_alerts.py``:

    zdx_list_alerts, zdx_get_alert, zdx_list_alert_affected_devices

ZDX SDK quirk: ``list_ongoing`` returns ``[alerts_obj]`` whose real rows hang
off ``alerts_obj.alerts``; ``list_affected_devices`` returns ``[affected_obj]``
with rows on ``affected_obj.devices``. Both are unwrapped via ``unwrap_nested``
before shaping. ``since`` is in HOURS (max 14 days = 336h).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many, shape_one
from zscaler_mcp.tools.zdx._common import scope_query_params, unwrap_nested

# =============================================================================
# INPUT MODELS
# =============================================================================


class _AlertScopeInput(BaseModel):
    """Shared scope/pagination filters for the alert list endpoints."""

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
        Field(
            default=None,
            ge=1,
            le=336,
            description="Look-back window in HOURS (ZDX default 2h, max 14 days = 336h).",
        ),
    ] = None
    offset: Annotated[
        Optional[str],
        Field(default=None, description="Pagination offset (the `next_offset` from a prior call)."),
    ] = None
    limit: Annotated[
        Optional[int], Field(default=None, ge=1, description="Items to return per request.")
    ] = None


class ListAlertsInput(_AlertScopeInput):
    """Inputs for listing ongoing ZDX alerts."""


class GetAlertInput(BaseModel):
    """Inputs for getting one ZDX alert."""

    alert_id: Annotated[str, Field(description="The unique alert ID (string, even if numeric).")]


class ListAffectedDevicesInput(_AlertScopeInput):
    """Inputs for listing devices affected by a ZDX alert."""

    alert_id: Annotated[str, Field(description="The unique alert ID (string, even if numeric).")]
    location_groups: Annotated[
        Optional[list[int]], Field(default=None, description="Filter by location group ID(s).")
    ] = None


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
    toolset="zdx_alerts",
    input_model=ListAlertsInput,
    is_list=True,
)
def zdx_list_alerts(args: ListAlertsInput) -> list[dict[str, Any]]:
    """List ongoing ZDX alerts.

    Read-only. Returns one triage row per ongoing alert (id, rule, severity,
    type, start time, impacted-device count). Filter by location/department/geo
    and the `since` HOURS window (max 336h). Use a returned alert `id` with
    `zdx_get_alert` or `zdx_list_alert_affected_devices`.
    """
    client = get_zscaler_client(service="zdx")
    qp = scope_query_params(
        location_id=args.location_id,
        department_id=args.department_id,
        geo_id=args.geo_id,
        since=args.since,
        offset=args.offset,
        limit=args.limit,
    )
    result, _, err = client.zdx.alerts.list_ongoing(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZDX alerts: {err}")
    return shape_many(unwrap_nested(result, "alerts"))


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_alerts",
    input_model=GetAlertInput,
    is_list=False,
)
def zdx_get_alert(args: GetAlertInput) -> dict[str, Any]:
    """Get one ZDX alert as a curated, agent-facing detail view.

    Read-only. Adds the impacted department / location / geolocation scope to the
    summary fields.
    """
    if not args.alert_id:
        raise ValueError("alert_id is required")
    client = get_zscaler_client(service="zdx")
    result, _, err = client.zdx.alerts.get_alert(args.alert_id)
    if err:
        raise RuntimeError(f"Failed to get ZDX alert {args.alert_id}: {err}")
    return shape_one(result.as_dict() if result else {})


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_alerts",
    input_model=ListAffectedDevicesInput,
    is_list=True,
)
def zdx_list_alert_affected_devices(args: ListAffectedDevicesInput) -> list[dict[str, Any]]:
    """List devices affected by a ZDX alert.

    Read-only. Returns one identifying row per affected device. Filter by
    location/department/geo, location groups, and the `since` HOURS window.
    """
    if not args.alert_id:
        raise ValueError("alert_id is required")
    client = get_zscaler_client(service="zdx")
    qp = scope_query_params(
        location_id=args.location_id,
        department_id=args.department_id,
        geo_id=args.geo_id,
        since=args.since,
        offset=args.offset,
        limit=args.limit,
        location_groups=args.location_groups,
    )
    result, _, err = client.zdx.alerts.list_affected_devices(args.alert_id, query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list affected devices for alert {args.alert_id}: {err}")
    return shape_many(unwrap_nested(result, "devices"))
