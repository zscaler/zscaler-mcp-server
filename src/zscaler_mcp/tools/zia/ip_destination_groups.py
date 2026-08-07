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
from zscaler_mcp.shaping import AgentView, shape_many, shape_one

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


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=ListInput,
    is_list=True,
)
def zia_list_ip_destination_groups(args: ListInput) -> list[dict[str, Any]]:
    """List ZIA IP destination groups."""
    client = get_zscaler_client(service="zia")
    qp = {"search": args.search} if args.search else {}
    groups, _, err = client.zia.cloud_firewall.list_ip_destination_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list IP destination groups: {err}")
    return shape_many([g.as_dict() for g in (groups or [])])


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=GetInput,
    is_list=False,
)
def zia_get_ip_destination_group(args: GetInput) -> dict[str, Any]:
    """Get a single ZIA IP destination group by ID with full members."""
    client = get_zscaler_client(service="zia")
    group, _, err = client.zia.cloud_firewall.get_ip_destination_group(args.group_id)
    if err:
        raise RuntimeError(f"Failed to get IP destination group {args.group_id}: {err}")
    return shape_one(group.as_dict())


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=CreateInput,
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
    return shape_one(group.as_dict())


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=UpdateInput,
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
    return shape_one(group.as_dict())


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=DeleteInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_ip_destination_group(args: DeleteInput) -> dict[str, Any]:
    """Delete a ZIA IP destination group (destructive). Activate after.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.cloud_firewall.delete_ip_destination_group(args.group_id)
    if err:
        raise RuntimeError(f"Failed to delete IP destination group {args.group_id}: {err}")
    return OperationResult(
        success=True, message=f"IP destination group {args.group_id} deleted successfully."
    ).model_dump()
