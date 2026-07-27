"""ZDX active devices — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zdx/active_devices.py``
(zdx_list_devices, zdx_get_device).

ZDX SDK quirk: ``list_devices`` returns ``[devices_obj]`` whose real rows hang
off ``devices_obj.devices``; ``get_device`` returns ``[device_detail]`` (a plain
single-element list). Both are unwrapped before shaping.
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


class ListDevicesInput(BaseModel):
    """Inputs for listing active ZDX devices."""

    emails: Annotated[
        Optional[list[str]], Field(default=None, description="Filter by user email address(es).")
    ] = None
    user_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Filter by user ID(s).")
    ] = None
    mac_address: Annotated[
        Optional[str], Field(default=None, description="Filter by device MAC address.")
    ] = None
    private_ipv4: Annotated[
        Optional[str], Field(default=None, description="Filter by device private IPv4 address.")
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
    offset: Annotated[
        Optional[str],
        Field(default=None, description="Pagination offset (the `next_offset` from a prior call)."),
    ] = None


class GetDeviceInput(BaseModel):
    """Inputs for getting one active ZDX device."""

    device_id: Annotated[str, Field(description="Device ID (string, even if numeric).")]
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


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_reports",
    input_model=ListDevicesInput,
    is_list=True,
)
def zdx_list_devices(args: ListDevicesInput) -> list[dict[str, Any]]:
    """List active ZDX devices.

    Read-only. Returns one identifying row per device (id, hostname, owning
    user). Filter by email, user ID, MAC/IP, location/department/geo, and the
    `since` HOURS window. Use a returned device `id` with `zdx_get_device` or the
    deep-trace / probe tools.
    """
    client = get_zscaler_client(service="zdx")

    qp = scope_query_params(
        location_id=args.location_id,
        department_id=args.department_id,
        geo_id=args.geo_id,
        since=args.since,
        emails=args.emails,
        user_ids=args.user_ids,
        mac_address=args.mac_address,
        private_ipv4=args.private_ipv4,
        offset=args.offset,
    )

    results, _, err = client.zdx.devices.list_devices(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZDX devices: {err}")

    raw_devices = unwrap_nested(results, "devices")
    return shape_many(raw_devices)


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_reports",
    input_model=GetDeviceInput,
    is_list=False,
)
def zdx_get_device(args: GetDeviceInput) -> dict[str, Any]:
    """Get one active ZDX device.

    Read-only. The ZDX SDK returns a single-element list; the device record is
    unwrapped and shaped to the identifying fields.
    """
    if not args.device_id:
        raise ValueError("device_id is required")

    client = get_zscaler_client(service="zdx")

    qp = scope_query_params(
        location_id=args.location_id,
        department_id=args.department_id,
        geo_id=args.geo_id,
        since=args.since,
    )

    result, _, err = client.zdx.devices.get_device(args.device_id, query_params=qp)
    if err:
        raise RuntimeError(f"Failed to get ZDX device {args.device_id}: {err}")

    if result and len(result) > 0:
        return shape_one(result[0].as_dict())
    return shape_one({})
