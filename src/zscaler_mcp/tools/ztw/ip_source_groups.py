"""ZTW IP source groups — list, list-lite, create, delete.

Mirrors v1's ``client.ztw.ip_source_groups`` calls. Structurally identical to
IP groups (a named set of source IPs) but a distinct SDK resource, so it gets
its own tools and views. The full and ``*_lite`` list endpoints are separate
tools, matching v1.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.utils import parse_list
from zscaler_mcp.registry import CREATE, DELETE, READ, tool
from zscaler_mcp.shaping import AgentView, coalesce, pick, shape_many

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListSourceGroupsInput(BaseModel):
    """Inputs for listing ZTW IP source groups."""

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


class CreateSourceGroupInput(BaseModel):
    """Inputs for creating a ZTW IP source group."""

    name: Annotated[str, Field(description="Group name.")]
    ip_addresses: Annotated[list[str], Field(description="Source IP addresses in the group.")]
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )


class DeleteSourceGroupInput(BaseModel):
    """Inputs for deleting a ZTW IP source group (destructive)."""

    group_id: Annotated[str, Field(description="Group ID (string, even if numeric).")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class SourceGroupSummary(AgentView):
    """Lean view of a ZTW IP source group."""

    id: str = Field(description="IP source group ID. Use this in follow-up calls.")
    name: str = Field(description="Display name.")
    description: Optional[str] = Field(default=None, description="Admin description.")
    ip_address_count: int = Field(description="Number of source IP addresses in the group.")


class SourceGroupDetail(SourceGroupSummary):
    """Full view — adds the source IP members."""

    ip_addresses: list[str] = Field(default_factory=list, description="Source IP members.")


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

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
    service="ztw",
    toolset="ztw",
    input_model=ListSourceGroupsInput,
    output_view=SourceGroupSummary,
    is_list=True,
)
def ztw_list_ip_source_groups(args: ListSourceGroupsInput) -> list[dict[str, Any]]:
    """List ZTW IP source groups as curated, agent-facing summaries.

    `search` is a server-side substring match on the group name. Read-only.
    """
    client = get_zscaler_client(service="ztw")
    api = client.ztw.ip_source_groups

    qp: dict[str, Any] = {"search": args.search} if args.search else {}
    groups, _, err = api.list_ip_source_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list IP source groups: {err}")

    return shape_many([g.as_dict() for g in (groups or [])], shape_summary)


@tool(
    action=READ,
    service="ztw",
    toolset="ztw",
    input_model=ListSourceGroupsInput,
    output_view=SourceGroupSummary,
    is_list=True,
)
def ztw_list_ip_source_groups_lite(args: ListSourceGroupsInput) -> list[dict[str, Any]]:
    """List ZTW IP source groups via the lighter SDK endpoint (read-only).

    Same curated shape as `ztw_list_ip_source_groups`; uses the lite endpoint.
    """
    client = get_zscaler_client(service="ztw")
    api = client.ztw.ip_source_groups

    qp: dict[str, Any] = {"search": args.search} if args.search else {}
    groups, _, err = api.list_ip_source_groups_lite(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list IP source groups (lite): {err}")

    return shape_many([g.as_dict() for g in (groups or [])], shape_summary)


@tool(
    action=CREATE,
    service="ztw",
    toolset="ztw",
    input_model=CreateSourceGroupInput,
    output_view=SourceGroupDetail,
    is_list=False,
)
def ztw_create_ip_source_group(args: CreateSourceGroupInput) -> dict[str, Any]:
    """Create a ZTW IP source group (write). Gated by HMAC confirmation + `--write-tools`."""
    if not args.name or not args.ip_addresses:
        raise ValueError("name and ip_addresses are required")

    ip_addresses = parse_list(args.ip_addresses)

    client = get_zscaler_client(service="ztw")
    api = client.ztw.ip_source_groups

    group, _, err = api.add_ip_source_group(
        name=args.name, description=args.description, ip_addresses=ip_addresses
    )
    if err:
        raise RuntimeError(f"Failed to create IP source group: {err}")
    return shape_detail(group.as_dict()).model_dump()


@tool(
    action=DELETE,
    service="ztw",
    toolset="ztw",
    input_model=DeleteSourceGroupInput,
    output_view=OperationResult,
    is_list=False,
)
def ztw_delete_ip_source_group(args: DeleteSourceGroupInput) -> dict[str, Any]:
    """Delete a ZTW IP source group (destructive write). Cannot be undone."""
    if not args.group_id:
        raise ValueError("group_id is required for delete")

    client = get_zscaler_client(service="ztw")
    api = client.ztw.ip_source_groups

    _, _, err = api.delete_ip_source_group(args.group_id)
    if err:
        raise RuntimeError(f"Failed to delete IP source group {args.group_id}: {err}")
    return OperationResult(
        success=True, message=f"IP source group {args.group_id} deleted successfully."
    ).model_dump()
