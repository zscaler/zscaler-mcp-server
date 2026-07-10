"""ZIA IP destination groups — list, get, create, update, delete.

Mirrors v1's ``client.zia.cloud_firewall`` IP destination group SDK calls.
Writes are staged until ``zia_activate_configuration``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.utils import parse_list
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, coalesce, pick, shape_many

_TYPE_PATTERN = "^(DSTN_IP|DSTN_FQDN|DSTN_DOMAIN|DSTN_OTHER)$"

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListInput(BaseModel):
    search: Annotated[
        Optional[str], Field(default=None, description="Substring match on group name.")
    ] = None


class GetInput(BaseModel):
    group_id: Annotated[str, Field(description="Destination group ID (string, even if numeric).")]


class CreateInput(BaseModel):
    name: Annotated[str, Field(description="Name of the destination group.")]
    type: Annotated[
        str,
        Field(pattern=_TYPE_PATTERN, description="DSTN_IP, DSTN_FQDN, DSTN_DOMAIN, or DSTN_OTHER."),
    ]
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    addresses: Annotated[
        Optional[list[str]],
        Field(default=None, description="IPs/FQDNs. Required for DSTN_IP or DSTN_FQDN."),
    ] = None
    countries: Annotated[
        Optional[list[str]],
        Field(default=None, description="Country codes (COUNTRY_XX). Optional for DSTN_OTHER."),
    ] = None
    ip_categories: Annotated[
        Optional[list[str]],
        Field(default=None, description="URL categories. Optional for DSTN_OTHER."),
    ] = None


class UpdateInput(CreateInput):
    group_id: Annotated[str, Field(description="Group ID to update.")]


class DeleteInput(BaseModel):
    group_id: Annotated[str, Field(description="Group ID to delete.")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class DestinationGroupSummary(AgentView):
    id: str = Field(description="Destination group ID. Use in follow-up calls.")
    name: str = Field(description="Display name.")
    type: Optional[str] = Field(default=None, description="Group type.")
    description: Optional[str] = Field(default=None, description="Admin description.")
    address_count: int = Field(description="Number of IP/FQDN members.")
    country_count: int = Field(description="Number of country members.")


class DestinationGroupDetail(DestinationGroupSummary):
    addresses: list[str] = Field(default_factory=list, description="IP/FQDN members.")
    countries: list[str] = Field(default_factory=list, description="COUNTRY_XX members.")
    ip_categories: list[str] = Field(default_factory=list, description="URL-category members.")


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


# =============================================================================
# SHAPERS
# =============================================================================


def _addresses(raw: dict[str, Any]) -> list[Any]:
    return coalesce(raw, "addresses", "ip_addresses", "ipAddresses")


def shape_summary(raw: dict[str, Any]) -> DestinationGroupSummary:
    return DestinationGroupSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        type=pick(raw, "type"),
        description=pick(raw, "description"),
        address_count=len(_addresses(raw)),
        country_count=len(coalesce(raw, "countries")),
    )


def shape_detail(raw: dict[str, Any]) -> DestinationGroupDetail:
    addrs = _addresses(raw)
    countries = coalesce(raw, "countries")
    return DestinationGroupDetail(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        type=pick(raw, "type"),
        description=pick(raw, "description"),
        address_count=len(addrs),
        country_count=len(countries),
        addresses=[str(a) for a in addrs],
        countries=[str(c) for c in countries],
        ip_categories=[str(c) for c in coalesce(raw, "ip_categories", "ipCategories")],
    )


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=ListInput,
    output_view=DestinationGroupSummary,
    is_list=True,
)
def zia_list_ip_destination_groups(args: ListInput) -> list[dict[str, Any]]:
    """List ZIA IP destination groups as curated summaries."""
    client = get_zscaler_client(service="zia")
    qp = {"search": args.search} if args.search else {}
    groups, _, err = client.zia.cloud_firewall.list_ip_destination_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list IP destination groups: {err}")
    return shape_many([g.as_dict() for g in (groups or [])], shape_summary)


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=GetInput,
    output_view=DestinationGroupDetail,
    is_list=False,
)
def zia_get_ip_destination_group(args: GetInput) -> dict[str, Any]:
    """Get a single ZIA IP destination group by ID with full members."""
    client = get_zscaler_client(service="zia")
    group, _, err = client.zia.cloud_firewall.get_ip_destination_group(args.group_id)
    if err:
        raise RuntimeError(f"Failed to get IP destination group {args.group_id}: {err}")
    return shape_detail(group.as_dict()).model_dump()


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=CreateInput,
    output_view=DestinationGroupDetail,
    is_list=False,
)
def zia_create_ip_destination_group(args: CreateInput) -> dict[str, Any]:
    """Create a ZIA IP destination group (write). Activate after."""
    client = get_zscaler_client(service="zia")
    group, _, err = client.zia.cloud_firewall.add_ip_destination_group(
        name=args.name,
        description=args.description,
        type=args.type,
        addresses=parse_list(args.addresses) if args.addresses is not None else None,
        countries=parse_list(args.countries) if args.countries is not None else None,
        ip_categories=parse_list(args.ip_categories) if args.ip_categories is not None else None,
    )
    if err:
        raise RuntimeError(f"Failed to create IP destination group: {err}")
    return shape_detail(group.as_dict()).model_dump()


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=UpdateInput,
    output_view=DestinationGroupDetail,
    is_list=False,
)
def zia_update_ip_destination_group(args: UpdateInput) -> dict[str, Any]:
    """Update a ZIA IP destination group (full-replace write). Activate after."""
    client = get_zscaler_client(service="zia")
    group, _, err = client.zia.cloud_firewall.update_ip_destination_group(
        group_id=args.group_id,
        name=args.name,
        description=args.description,
        type=args.type,
        addresses=parse_list(args.addresses) if args.addresses is not None else None,
        countries=parse_list(args.countries) if args.countries is not None else None,
        ip_categories=parse_list(args.ip_categories) if args.ip_categories is not None else None,
    )
    if err:
        raise RuntimeError(f"Failed to update IP destination group {args.group_id}: {err}")
    return shape_detail(group.as_dict()).model_dump()


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=DeleteInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_ip_destination_group(args: DeleteInput) -> dict[str, Any]:
    """Delete a ZIA IP destination group (destructive). Activate after."""
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.cloud_firewall.delete_ip_destination_group(args.group_id)
    if err:
        raise RuntimeError(f"Failed to delete IP destination group {args.group_id}: {err}")
    return OperationResult(
        success=True, message=f"IP destination group {args.group_id} deleted successfully."
    ).model_dump()
