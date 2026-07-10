"""ZIA IP source groups — list, get, create, update, delete.

Mirrors v1's ``client.zia.cloud_firewall`` IP source group SDK calls, returning
curated views. Writes are staged until ``zia_activate_configuration``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.utils import parse_list
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, coalesce, pick, shape_many

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListInput(BaseModel):
    search: Annotated[
        Optional[str], Field(default=None, description="Substring match on group name.")
    ] = None


class GetInput(BaseModel):
    group_id: Annotated[str, Field(description="IP source group ID (string, even if numeric).")]


class CreateInput(BaseModel):
    name: Annotated[str, Field(description="Group name.")]
    ip_addresses: Annotated[list[str], Field(description="IP addresses / CIDRs in the group.")]
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )


class UpdateInput(BaseModel):
    group_id: Annotated[str, Field(description="Group ID to update.")]
    name: Annotated[str, Field(description="Group name (full-replace; required by the API).")]
    ip_addresses: Annotated[
        list[str], Field(description="Full IP/CIDR set (replaces existing members).")
    ]
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )


class DeleteInput(BaseModel):
    group_id: Annotated[str, Field(description="Group ID to delete.")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class SourceGroupSummary(AgentView):
    id: str = Field(description="Source group ID. Use in follow-up calls.")
    name: str = Field(description="Display name.")
    description: Optional[str] = Field(default=None, description="Admin description.")
    ip_address_count: int = Field(description="Number of IP/CIDR members.")


class SourceGroupDetail(SourceGroupSummary):
    ip_addresses: list[str] = Field(default_factory=list, description="IP/CIDR members.")


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


# =============================================================================
# SHAPERS
# =============================================================================


def _ips(raw: dict[str, Any]) -> list[Any]:
    return coalesce(raw, "ip_addresses", "ipAddresses", "addresses")


def shape_summary(raw: dict[str, Any]) -> SourceGroupSummary:
    return SourceGroupSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        description=pick(raw, "description"),
        ip_address_count=len(_ips(raw)),
    )


def shape_detail(raw: dict[str, Any]) -> SourceGroupDetail:
    ips = _ips(raw)
    return SourceGroupDetail(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        description=pick(raw, "description"),
        ip_address_count=len(ips),
        ip_addresses=[str(i) for i in ips],
    )


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=ListInput,
    output_view=SourceGroupSummary,
    is_list=True,
)
def zia_list_ip_source_groups(args: ListInput) -> list[dict[str, Any]]:
    """List ZIA IP source groups as curated summaries."""
    client = get_zscaler_client(service="zia")
    qp = {"search": args.search} if args.search else {}
    groups, _, err = client.zia.cloud_firewall.list_ip_source_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list IP source groups: {err}")
    return shape_many([g.as_dict() for g in (groups or [])], shape_summary)


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=GetInput,
    output_view=SourceGroupDetail,
    is_list=False,
)
def zia_get_ip_source_group(args: GetInput) -> dict[str, Any]:
    """Get a single ZIA IP source group by ID with its full member list."""
    client = get_zscaler_client(service="zia")
    group, _, err = client.zia.cloud_firewall.get_ip_source_group(args.group_id)
    if err:
        raise RuntimeError(f"Failed to get IP source group {args.group_id}: {err}")
    return shape_detail(group.as_dict()).model_dump()


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=CreateInput,
    output_view=SourceGroupDetail,
    is_list=False,
)
def zia_create_ip_source_group(args: CreateInput) -> dict[str, Any]:
    """Create a ZIA IP source group (write). Call zia_activate_configuration after."""
    client = get_zscaler_client(service="zia")
    group, _, err = client.zia.cloud_firewall.add_ip_source_group(
        name=args.name,
        description=args.description,
        ip_addresses=parse_list(args.ip_addresses),
    )
    if err:
        raise RuntimeError(f"Failed to create IP source group: {err}")
    return shape_detail(group.as_dict()).model_dump()


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=UpdateInput,
    output_view=SourceGroupDetail,
    is_list=False,
)
def zia_update_ip_source_group(args: UpdateInput) -> dict[str, Any]:
    """Update a ZIA IP source group (full-replace write). Activate after."""
    client = get_zscaler_client(service="zia")
    group, _, err = client.zia.cloud_firewall.update_ip_source_group(
        group_id=args.group_id,
        name=args.name,
        description=args.description,
        ip_addresses=parse_list(args.ip_addresses),
    )
    if err:
        raise RuntimeError(f"Failed to update IP source group {args.group_id}: {err}")
    return shape_detail(group.as_dict()).model_dump()


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=DeleteInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_ip_source_group(args: DeleteInput) -> dict[str, Any]:
    """Delete a ZIA IP source group (destructive). Activate after."""
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.cloud_firewall.delete_ip_source_group(args.group_id)
    if err:
        raise RuntimeError(f"Failed to delete IP source group {args.group_id}: {err}")
    return OperationResult(
        success=True, message=f"IP source group {args.group_id} deleted successfully."
    ).model_dump()
