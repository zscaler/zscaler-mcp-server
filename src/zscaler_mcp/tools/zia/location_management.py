"""ZIA locations & location groups — list/get/create/update/delete.

Mirrors v1's ``client.zia.locations`` SDK calls. Common location fields are typed;
less-common knobs ride an ``advanced`` passthrough dict (camelCase as the SDK
expects). Writes are staged until ``zia_activate_configuration``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, coalesce, pick, shape_many

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListLocationsInput(BaseModel):
    search: Annotated[
        Optional[str], Field(default=None, description="Substring match on location name.")
    ] = None


class GetLocationInput(BaseModel):
    location_id: Annotated[str, Field(description="Location ID (string, even if numeric).")]


class _LocationBody(BaseModel):
    name: Annotated[str, Field(description="Location name.")]
    country: Annotated[
        Optional[str], Field(default=None, description="Country, e.g. 'CANADA'.")
    ] = None
    tz: Annotated[
        Optional[str], Field(default=None, description="Timezone, e.g. 'CANADA_AMERICA_VANCOUVER'.")
    ] = None
    ip_addresses: Annotated[
        Optional[list[str]],
        Field(default=None, description="Static IPs/CIDRs/GRE addrs. Required unless VPN-based."),
    ] = None
    description: Annotated[Optional[str], Field(default=None, description="Notes.")] = None
    advanced: Annotated[
        Optional[dict[str, Any]],
        Field(
            default=None,
            description=(
                "Passthrough for less-common SDK fields in camelCase: vpnCredentials, "
                "profile, xffForwardEnabled, authRequired, aupEnabled, ofwEnabled, "
                "surrogateIP, etc. Merged into the create/update payload as-is."
            ),
        ),
    ] = None


class CreateLocationInput(_LocationBody):
    pass


class UpdateLocationInput(_LocationBody):
    location_id: Annotated[str, Field(description="Location ID to update.")]


class DeleteLocationInput(BaseModel):
    location_id: Annotated[str, Field(description="Location ID to delete.")]


class ListLocationGroupsInput(BaseModel):
    search: Annotated[
        Optional[str], Field(default=None, description="Substring match on group name.")
    ] = None
    name: Annotated[Optional[str], Field(default=None, description="Exact group name filter.")] = (
        None
    )


class GetLocationGroupInput(BaseModel):
    group_id: Annotated[str, Field(description="Location group ID (string, even if numeric).")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class LocationSummary(AgentView):
    id: str = Field(description="Location ID. Use in follow-up calls.")
    name: str = Field(description="Display name.")
    country: Optional[str] = Field(default=None, description="Country.")
    tz: Optional[str] = Field(default=None, description="Timezone.")
    ip_address_count: int = Field(description="Number of configured IP addresses.")
    auth_required: Optional[bool] = Field(default=None, description="Authentication required flag.")


class LocationDetail(LocationSummary):
    ip_addresses: list[str] = Field(default_factory=list, description="Configured IP addresses.")
    profile: Optional[str] = Field(default=None, description="Profile tag (CORPORATE/SERVER/...).")
    description: Optional[str] = Field(default=None, description="Notes.")
    xff_forward_enabled: Optional[bool] = Field(default=None, description="XFF forwarding flag.")
    surrogate_ip: Optional[bool] = Field(default=None, description="Surrogate IP flag.")


class LocationGroupSummary(AgentView):
    id: str = Field(description="Location group ID.")
    name: str = Field(description="Display name.")
    group_type: Optional[str] = Field(default=None, description="DYNAMIC or STATIC.")
    location_count: int = Field(description="Number of member locations.")


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


# =============================================================================
# SHAPERS
# =============================================================================


def _ips(raw: dict[str, Any]) -> list[Any]:
    return coalesce(raw, "ip_addresses", "ipAddresses")


def shape_loc_summary(raw: dict[str, Any]) -> LocationSummary:
    return LocationSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        country=pick(raw, "country"),
        tz=pick(raw, "tz"),
        ip_address_count=len(_ips(raw)),
        auth_required=pick(raw, "auth_required", "authRequired"),
    )


def shape_loc_detail(raw: dict[str, Any]) -> LocationDetail:
    ips = _ips(raw)
    return LocationDetail(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        country=pick(raw, "country"),
        tz=pick(raw, "tz"),
        ip_address_count=len(ips),
        auth_required=pick(raw, "auth_required", "authRequired"),
        ip_addresses=[str(i) for i in ips],
        profile=pick(raw, "profile"),
        description=pick(raw, "description"),
        xff_forward_enabled=pick(raw, "xff_forward_enabled", "xffForwardEnabled"),
        surrogate_ip=pick(raw, "surrogate_ip", "surrogateIP"),
    )


def shape_group_summary(raw: dict[str, Any]) -> LocationGroupSummary:
    return LocationGroupSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        group_type=pick(raw, "group_type", "groupType"),
        location_count=len(coalesce(raw, "locations")),
    )


def _build_location_body(args: _LocationBody) -> dict[str, Any]:
    body: dict[str, Any] = {"name": args.name}
    if args.country is not None:
        body["country"] = args.country
    if args.tz is not None:
        body["tz"] = args.tz
    if args.ip_addresses is not None:
        body["ip_addresses"] = args.ip_addresses
    if args.description is not None:
        body["description"] = args.description
    if args.advanced:
        body.update(args.advanced)
    return body


# =============================================================================
# LOCATION TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zia",
    toolset="zia_locations",
    input_model=ListLocationsInput,
    output_view=LocationSummary,
    is_list=True,
)
def zia_list_locations(args: ListLocationsInput) -> list[dict[str, Any]]:
    """List ZIA locations as curated summaries."""
    client = get_zscaler_client(service="zia")
    qp = {"search": args.search} if args.search else {}
    locs, _, err = client.zia.locations.list_locations(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list locations: {err}")
    return shape_many([loc.as_dict() for loc in (locs or [])], shape_loc_summary)


@tool(
    action=READ,
    service="zia",
    toolset="zia_locations",
    input_model=GetLocationInput,
    output_view=LocationDetail,
    is_list=False,
)
def zia_get_location(args: GetLocationInput) -> dict[str, Any]:
    """Get a single ZIA location by ID with its full configuration."""
    client = get_zscaler_client(service="zia")
    loc, _, err = client.zia.locations.get_location(args.location_id)
    if err:
        raise RuntimeError(f"Failed to get location {args.location_id}: {err}")
    return shape_loc_detail(loc.as_dict()).model_dump()


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_locations",
    input_model=CreateLocationInput,
    output_view=LocationDetail,
    is_list=False,
)
def zia_create_location(args: CreateLocationInput) -> dict[str, Any]:
    """Create a ZIA location (write). Needs ipAddresses or vpnCredentials. Activate after."""
    body = _build_location_body(args)
    if not body.get("ip_addresses") and not (args.advanced or {}).get("vpnCredentials"):
        raise ValueError(
            "Location creation requires ip_addresses or advanced.vpnCredentials. "
            "Create a static IP first with zia_create_static_ip if needed."
        )
    client = get_zscaler_client(service="zia")
    created, _, err = client.zia.locations.add_location(**body)
    if err:
        raise RuntimeError(f"Failed to create location: {err}")
    return shape_loc_detail(created.as_dict()).model_dump()


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_locations",
    input_model=UpdateLocationInput,
    output_view=LocationDetail,
    is_list=False,
)
def zia_update_location(args: UpdateLocationInput) -> dict[str, Any]:
    """Update a ZIA location (write). Activate after."""
    body = _build_location_body(args)
    client = get_zscaler_client(service="zia")
    updated, _, err = client.zia.locations.update_location(args.location_id, **body)
    if err:
        raise RuntimeError(f"Failed to update location {args.location_id}: {err}")
    return shape_loc_detail(updated.as_dict()).model_dump()


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_locations",
    input_model=DeleteLocationInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_location(args: DeleteLocationInput) -> dict[str, Any]:
    """Delete a ZIA location (destructive). Activate after."""
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.locations.delete_location(args.location_id)
    if err:
        raise RuntimeError(f"Failed to delete location {args.location_id}: {err}")
    return OperationResult(
        success=True, message=f"Location {args.location_id} deleted successfully."
    ).model_dump()


# =============================================================================
# LOCATION GROUP TOOLS (read-only)
# =============================================================================


@tool(
    action=READ,
    service="zia",
    toolset="zia_locations",
    input_model=ListLocationGroupsInput,
    output_view=LocationGroupSummary,
    is_list=True,
)
def zia_list_location_groups(args: ListLocationGroupsInput) -> list[dict[str, Any]]:
    """List ZIA location groups as curated summaries."""
    client = get_zscaler_client(service="zia")
    qp: dict[str, Any] = {}
    if args.search:
        qp["search"] = args.search
    if args.name:
        qp["name"] = args.name
    groups, _, err = client.zia.locations.list_location_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list location groups: {err}")
    return shape_many([g.as_dict() for g in (groups or [])], shape_group_summary)


@tool(
    action=READ,
    service="zia",
    toolset="zia_locations",
    input_model=GetLocationGroupInput,
    output_view=LocationGroupSummary,
    is_list=False,
)
def zia_get_location_group(args: GetLocationGroupInput) -> dict[str, Any]:
    """Get a single ZIA location group by ID."""
    client = get_zscaler_client(service="zia")
    group, _, err = client.zia.locations.get_location_group(args.group_id)
    if err:
        raise RuntimeError(f"Failed to get location group {args.group_id}: {err}")
    return shape_group_summary(group.as_dict()).model_dump()
