"""ZTW IP groups — list, list-lite, create, delete.

Mirrors v1's ``client.ztw.ip_groups`` calls. An IP group is a simple named set
of IP addresses; the full record surfaces the count plus (in detail) the
members. The full and ``*_lite`` list endpoints are separate tools, matching v1.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.utils import parse_list
from zscaler_mcp.registry import CREATE, DELETE, READ, tool
from zscaler_mcp.shaping import AgentView, shape_many, shape_one

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListIPGroupsInput(BaseModel):
    """Inputs for listing ZTW IP groups."""

    search: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                "Server-side substring match on the group name. An empty result "
                "means no group name contains this string — do not retry broadened."
            ),
        ),
    ] = None


class CreateIPGroupInput(BaseModel):
    """Inputs for creating a ZTW IP group."""

    name: Annotated[str, Field(description="Group name.")]
    ip_addresses: Annotated[list[str], Field(description="IP addresses in the group.")]
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )


class DeleteIPGroupInput(BaseModel):
    """Inputs for deleting a ZTW IP group (destructive)."""

    group_id: Annotated[str, Field(description="Group ID (string, even if numeric).")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")




# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="ztw",
    toolset="ztw",
    input_model=ListIPGroupsInput,
    is_list=True,
)
def ztw_list_ip_groups(args: ListIPGroupsInput) -> list[dict[str, Any]]:
    """List ZTW IP groups.

    `search` is a server-side substring match on the group name. Read-only.
    """
    client = get_zscaler_client(service="ztw")
    api = client.ztw.ip_groups

    qp: dict[str, Any] = {"search": args.search} if args.search else {}
    groups, _, err = api.list_ip_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list IP groups: {err}")

    return shape_many([g.as_dict() for g in (groups or [])])


@tool(
    action=READ,
    service="ztw",
    toolset="ztw",
    input_model=ListIPGroupsInput,
    is_list=True,
)
def ztw_list_ip_groups_lite(args: ListIPGroupsInput) -> list[dict[str, Any]]:
    """List ZTW IP groups via the lighter SDK endpoint (read-only).

    Same records as `ztw_list_ip_groups`; uses the lite endpoint.
    """
    client = get_zscaler_client(service="ztw")
    api = client.ztw.ip_groups

    qp: dict[str, Any] = {"search": args.search} if args.search else {}
    groups, _, err = api.list_ip_groups_lite(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list IP groups (lite): {err}")

    return shape_many([g.as_dict() for g in (groups or [])])


@tool(
    action=CREATE,
    service="ztw",
    toolset="ztw",
    input_model=CreateIPGroupInput,
    is_list=False,
)
def ztw_create_ip_group(args: CreateIPGroupInput) -> dict[str, Any]:
    """Create a ZTW IP group (write). Gated by HMAC confirmation + `--write-tools`."""
    if not args.name or not args.ip_addresses:
        raise ValueError("name and ip_addresses are required")

    ip_addresses = parse_list(args.ip_addresses)

    client = get_zscaler_client(service="ztw")
    api = client.ztw.ip_groups

    group, _, err = api.add_ip_group(
        name=args.name, description=args.description, ip_addresses=ip_addresses
    )
    if err:
        raise RuntimeError(f"Failed to create IP group: {err}")
    return shape_one(group.as_dict())


@tool(
    action=DELETE,
    service="ztw",
    toolset="ztw",
    input_model=DeleteIPGroupInput,
    output_view=OperationResult,
    is_list=False,
)
def ztw_delete_ip_group(args: DeleteIPGroupInput) -> dict[str, Any]:
    """Delete a ZTW IP group (destructive write). Cannot be undone."""
    if not args.group_id:
        raise ValueError("group_id is required for delete")

    client = get_zscaler_client(service="ztw")
    api = client.ztw.ip_groups

    _, _, err = api.delete_ip_group(args.group_id)
    if err:
        raise RuntimeError(f"Failed to delete IP group {args.group_id}: {err}")
    return OperationResult(
        success=True, message=f"IP group {args.group_id} deleted successfully."
    ).model_dump()
