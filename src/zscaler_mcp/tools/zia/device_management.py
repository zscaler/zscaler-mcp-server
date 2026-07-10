"""ZIA device management — device groups, devices, devices-lite (read-only).

Mirrors v1's ``client.zia.device_management`` SDK calls. NOTE: this data overlaps
ZCC's device tools; disabling ZCC does not remove these ZIA device tools.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many


class ListDeviceGroupsInput(BaseModel):
    include_device_info: Annotated[
        Optional[bool], Field(default=None, description="Include device info in the response.")
    ] = None
    include_pseudo_groups: Annotated[
        Optional[bool], Field(default=None, description="Include pseudo (auto) groups.")
    ] = None


class ListDevicesInput(BaseModel):
    name: Annotated[Optional[str], Field(default=None, description="Filter by device name.")] = None
    user_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Filter by owning user IDs.")
    ] = None
    include_all: Annotated[
        Optional[bool], Field(default=None, description="Include all devices regardless of state.")
    ] = None
    page: Annotated[Optional[int], Field(default=None, description="Page number.")] = None
    page_size: Annotated[Optional[int], Field(default=None, description="Items per page.")] = None


class _NoArgs(BaseModel):
    pass


class DeviceGroupSummary(AgentView):
    id: str = Field(description="Device group ID.")
    name: str = Field(description="Display name.")
    device_count: Optional[int] = Field(default=None, description="Number of devices, if reported.")


class DeviceSummary(AgentView):
    id: str = Field(description="Device ID.")
    name: Optional[str] = Field(default=None, description="Device name.")
    owner: Optional[str] = Field(default=None, description="Owning user.")
    os_type: Optional[str] = Field(default=None, description="Operating system type.")


def shape_group(raw: dict[str, Any]) -> DeviceGroupSummary:
    return DeviceGroupSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        device_count=pick(raw, "device_count", "deviceCount"),
    )


def shape_device(raw: dict[str, Any]) -> DeviceSummary:
    return DeviceSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name"),
        owner=pick(raw, "owner", "user_name", "userName"),
        os_type=pick(raw, "os_type", "osType"),
    )


@tool(
    action=READ,
    service="zia",
    toolset="zia_devices",
    input_model=ListDeviceGroupsInput,
    output_view=DeviceGroupSummary,
    is_list=True,
)
def zia_list_device_groups(args: ListDeviceGroupsInput) -> list[dict[str, Any]]:
    """List ZIA device groups as curated summaries."""
    client = get_zscaler_client(service="zia")
    qp: dict[str, Any] = {}
    if args.include_device_info is not None:
        qp["include_device_info"] = args.include_device_info
    if args.include_pseudo_groups is not None:
        qp["include_pseudo_groups"] = args.include_pseudo_groups
    groups, _, err = client.zia.device_management.list_device_groups(query_params=qp or None)
    if err:
        raise RuntimeError(f"Failed to list device groups: {err}")
    return shape_many([g.as_dict() for g in (groups or [])], shape_group)


@tool(
    action=READ,
    service="zia",
    toolset="zia_devices",
    input_model=ListDevicesInput,
    output_view=DeviceSummary,
    is_list=True,
)
def zia_list_devices(args: ListDevicesInput) -> list[dict[str, Any]]:
    """List ZIA devices as curated summaries."""
    client = get_zscaler_client(service="zia")
    qp: dict[str, Any] = {}
    if args.name:
        qp["name"] = args.name
    if args.user_ids:
        qp["user_ids"] = args.user_ids
    if args.include_all is not None:
        qp["include_all"] = args.include_all
    if args.page is not None:
        qp["page"] = args.page
    if args.page_size is not None:
        qp["page_size"] = args.page_size
    devices, _, err = client.zia.device_management.list_devices(query_params=qp or None)
    if err:
        raise RuntimeError(f"Failed to list devices: {err}")
    return shape_many([d.as_dict() for d in (devices or [])], shape_device)


@tool(
    action=READ,
    service="zia",
    toolset="zia_devices",
    input_model=_NoArgs,
    output_view=DeviceSummary,
    is_list=True,
)
def zia_list_devices_lite(args: _NoArgs) -> list[dict[str, Any]]:
    """List ZIA devices via the lighter endpoint (id/name only)."""
    client = get_zscaler_client(service="zia")
    devices, _, err = client.zia.device_management.list_device_lite()
    if err:
        raise RuntimeError(f"Failed to list devices (lite): {err}")
    return shape_many([d.as_dict() for d in (devices or [])], shape_device)
