"""ZIA network application groups — list/get/create/update/delete.

Mirrors v1's ``network_app_groups.py``. App groups are admin-managed. Backed by
``client.zia.cloud_firewall``. Writes are staged until ``zia_activate_configuration``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.utils import parse_list
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, shape_many, shape_one


class ListGroupsInput(BaseModel):
    search: Annotated[
        Optional[str], Field(default=None, description="Substring match on group name.")
    ] = None


class GetGroupInput(BaseModel):
    group_id: Annotated[str, Field(description="App group ID (string, even if numeric).")]


class CreateGroupInput(BaseModel):
    name: Annotated[str, Field(description="Group name.")]
    network_applications: Annotated[
        list[str], Field(description="Network application IDs to include.")
    ]
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )


class UpdateGroupInput(BaseModel):
    group_id: Annotated[str, Field(description="Group ID to update.")]
    name: Annotated[str, Field(description="Group name (required by API on update).")]
    network_applications: Annotated[
        list[str], Field(description="Full app-ID set (replaces existing members).")
    ]
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )


class DeleteGroupInput(BaseModel):
    group_id: Annotated[str, Field(description="Group ID to delete.")]


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")




@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=ListGroupsInput,
    is_list=True,
)
def zia_list_network_app_groups(args: ListGroupsInput) -> list[dict[str, Any]]:
    """List ZIA network application groups."""
    client = get_zscaler_client(service="zia")
    qp = {"search": args.search} if args.search else {}
    groups, _, err = client.zia.cloud_firewall.list_network_app_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list network app groups: {err}")
    return shape_many([g.as_dict() for g in (groups or [])])


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=GetGroupInput,
    is_list=False,
)
def zia_get_network_app_group(args: GetGroupInput) -> dict[str, Any]:
    """Get a single ZIA network application group by ID with members."""
    client = get_zscaler_client(service="zia")
    group, _, err = client.zia.cloud_firewall.get_network_app_group(args.group_id)
    if err:
        raise RuntimeError(f"Failed to get network app group {args.group_id}: {err}")
    return shape_one(group.as_dict())


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=CreateGroupInput,
    is_list=False,
)
def zia_create_network_app_group(args: CreateGroupInput) -> dict[str, Any]:
    """Create a ZIA network application group (write). Activate after."""
    client = get_zscaler_client(service="zia")
    group, _, err = client.zia.cloud_firewall.add_network_app_group(
        name=args.name,
        description=args.description,
        network_applications=parse_list(args.network_applications),
    )
    if err:
        raise RuntimeError(f"Failed to create network app group: {err}")
    return shape_one(group.as_dict())


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=UpdateGroupInput,
    is_list=False,
)
def zia_update_network_app_group(args: UpdateGroupInput) -> dict[str, Any]:
    """Update a ZIA network application group (full-replace write). Activate after."""
    client = get_zscaler_client(service="zia")
    group, _, err = client.zia.cloud_firewall.update_network_app_group(
        group_id=args.group_id,
        name=args.name,
        description=args.description,
        network_applications=parse_list(args.network_applications),
    )
    if err:
        raise RuntimeError(f"Failed to update network app group {args.group_id}: {err}")
    return shape_one(group.as_dict())


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=DeleteGroupInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_network_app_group(args: DeleteGroupInput) -> dict[str, Any]:
    """Delete a ZIA network application group (destructive). Activate after."""
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.cloud_firewall.delete_network_app_group(args.group_id)
    if err:
        raise RuntimeError(f"Failed to delete network app group {args.group_id}: {err}")
    return OperationResult(
        success=True, message=f"Network app group {args.group_id} deleted successfully."
    ).model_dump()
