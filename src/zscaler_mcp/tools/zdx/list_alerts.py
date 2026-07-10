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
from zscaler_mcp.shaping import AgentView, pick, shape_many
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


class AlertSummary(AgentView):
    """Lean view — what an agent needs to triage a ZDX alert."""

    id: str = Field(description="Alert ID. Use this with `zdx_get_alert` / affected-devices.")
    rule_name: Optional[str] = Field(default=None, description="Alert rule name.")
    severity: Optional[str] = Field(default=None, description="Alert severity (decision-bearing).")
    alert_type: Optional[str] = Field(default=None, description="Alert type/category.")
    started_on: Optional[str] = Field(default=None, description="When the alert started.")
    ended_on: Optional[str] = Field(default=None, description="When the alert ended (historical).")
    num_devices: Optional[int] = Field(
        default=None, description="Number of impacted devices (impact signal)."
    )
    application_name: Optional[str] = Field(
        default=None, description="Affected application, if any."
    )


class AlertDetail(AlertSummary):
    """Full view — summary plus the impacted-scope fields ZDX returns on get."""

    impacted_departments: list[str] = Field(
        default_factory=list, description="Departments impacted by the alert."
    )
    impacted_locations: list[str] = Field(
        default_factory=list, description="Zscaler locations impacted by the alert."
    )
    impacted_geolocations: list[str] = Field(
        default_factory=list, description="Geolocations impacted by the alert."
    )


class AffectedDeviceSummary(AgentView):
    """Lean view of a device impacted by an alert."""

    id: str = Field(description="Device ID. Use in follow-up ZDX device/trace calls.")
    name: Optional[str] = Field(default=None, description="Device hostname/name.")
    user_id: Optional[str] = Field(default=None, description="Owning user ID (relational).")
    user_name: Optional[str] = Field(default=None, description="Owning user (name/email).")


# =============================================================================
# SHAPERS
# =============================================================================


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _names(raw: dict[str, Any], *keys: str) -> list[str]:
    """Extract a list of human names from a list-of-dicts (or list-of-str) field."""
    for key in keys:
        value = raw.get(key)
        if isinstance(value, list):
            out: list[str] = []
            for item in value:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("id")
                    if name is not None:
                        out.append(str(name))
                elif item is not None:
                    out.append(str(item))
            return out
    return []


def _shape_alert_summary(raw: dict[str, Any]) -> AlertSummary:
    return AlertSummary(
        id=str(pick(raw, "id", "alert_id", default="")),
        rule_name=pick(raw, "rule_name", "ruleName", "name"),
        severity=pick(raw, "severity"),
        alert_type=pick(raw, "alert_type", "alertType", "type"),
        started_on=_opt_str(pick(raw, "started_on", "startedOn", "started")),
        ended_on=_opt_str(pick(raw, "ended_on", "endedOn", "ended")),
        num_devices=pick(raw, "num_devices", "numDevices", "device_count"),
        application_name=pick(raw, "application_name", "applicationName", "app_name"),
    )


def _shape_alert_detail(raw: dict[str, Any]) -> AlertDetail:
    base = _shape_alert_summary(raw)
    return AlertDetail(
        **base.model_dump(),
        impacted_departments=_names(
            raw, "impacted_departments", "impactedDepartments", "departments"
        ),
        impacted_locations=_names(raw, "impacted_locations", "impactedLocations", "locations"),
        impacted_geolocations=_names(
            raw, "impacted_geolocations", "impactedGeolocations", "geolocations"
        ),
    )


def _shape_affected_device(raw: dict[str, Any]) -> AffectedDeviceSummary:
    user = pick(raw, "userdetails", "user", default={})
    if not isinstance(user, dict):
        user = {}
    return AffectedDeviceSummary(
        id=str(pick(raw, "id", "device_id", default="")),
        name=pick(raw, "name", "hostname"),
        user_id=_opt_str(pick(raw, "user_id", "userId") or user.get("id")),
        user_name=pick(raw, "user_name", "userName") or user.get("name") or user.get("email"),
    )


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_alerts",
    input_model=ListAlertsInput,
    output_view=AlertSummary,
    is_list=True,
)
def zdx_list_alerts(args: ListAlertsInput) -> list[dict[str, Any]]:
    """List ongoing ZDX alerts as curated, agent-facing views.

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
    return shape_many(unwrap_nested(result, "alerts"), _shape_alert_summary)


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_alerts",
    input_model=GetAlertInput,
    output_view=AlertDetail,
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
    return _shape_alert_detail(result.as_dict() if result else {}).model_dump()


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_alerts",
    input_model=ListAffectedDevicesInput,
    output_view=AffectedDeviceSummary,
    is_list=True,
)
def zdx_list_alert_affected_devices(args: ListAffectedDevicesInput) -> list[dict[str, Any]]:
    """List devices affected by a ZDX alert as curated, agent-facing views.

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
    return shape_many(unwrap_nested(result, "devices"), _shape_affected_device)
