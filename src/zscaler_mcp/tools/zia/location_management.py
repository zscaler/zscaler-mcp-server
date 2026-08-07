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
from zscaler_mcp.shaping import AgentView, shape_many, shape_one

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


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


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
    is_list=True,
)
def zia_list_locations(args: ListLocationsInput) -> list[dict[str, Any]]:
    """List ZIA locations."""
    client = get_zscaler_client(service="zia")
    qp = {"search": args.search} if args.search else {}
    locs, _, err = client.zia.locations.list_locations(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list locations: {err}")
    return shape_many([loc.as_dict() for loc in (locs or [])])


@tool(
    action=READ,
    service="zia",
    toolset="zia_locations",
    input_model=GetLocationInput,
    is_list=False,
)
def zia_get_location(args: GetLocationInput) -> dict[str, Any]:
    """Get a single ZIA location by ID with its full configuration."""
    client = get_zscaler_client(service="zia")
    loc, _, err = client.zia.locations.get_location(args.location_id)
    if err:
        raise RuntimeError(f"Failed to get location {args.location_id}: {err}")
    return shape_one(loc.as_dict())


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_locations",
    input_model=CreateLocationInput,
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
    return shape_one(created.as_dict())


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_locations",
    input_model=UpdateLocationInput,
    is_list=False,
)
def zia_update_location(args: UpdateLocationInput) -> dict[str, Any]:
    """Update a ZIA location (write). Activate after."""
    body = _build_location_body(args)
    client = get_zscaler_client(service="zia")
    updated, _, err = client.zia.locations.update_location(args.location_id, **body)
    if err:
        raise RuntimeError(f"Failed to update location {args.location_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_locations",
    input_model=DeleteLocationInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_location(args: DeleteLocationInput) -> dict[str, Any]:
    """Delete a ZIA location (destructive). Activate after.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
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
    is_list=True,
)
def zia_list_location_groups(args: ListLocationGroupsInput) -> list[dict[str, Any]]:
    """List ZIA location groups."""
    client = get_zscaler_client(service="zia")
    qp: dict[str, Any] = {}
    if args.search:
        qp["search"] = args.search
    if args.name:
        qp["name"] = args.name
    groups, _, err = client.zia.locations.list_location_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list location groups: {err}")
    return shape_many([g.as_dict() for g in (groups or [])])


@tool(
    action=READ,
    service="zia",
    toolset="zia_locations",
    input_model=GetLocationGroupInput,
    is_list=False,
)
def zia_get_location_group(args: GetLocationGroupInput) -> dict[str, Any]:
    """Get a single ZIA location group by ID."""
    client = get_zscaler_client(service="zia")
    group, _, err = client.zia.locations.get_location_group(args.group_id)
    if err:
        raise RuntimeError(f"Failed to get location group {args.group_id}: {err}")
    return shape_one(group.as_dict())
