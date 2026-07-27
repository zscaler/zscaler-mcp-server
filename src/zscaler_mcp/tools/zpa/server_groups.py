"""ZPA server groups — agent-first v2 CRUD tools.

Mirrors v1's ``zscaler_mcp/tools/zpa/server_groups.py``, preserving its
business rules: a server group must bind at least one App Connector Group, and
``dynamic_discovery=False`` requires explicit ``server_ids``.

    zpa_list_server_groups   (READ)
    zpa_get_server_group     (READ)
    zpa_create_server_group  (CREATE)
    zpa_update_server_group  (UPDATE)
    zpa_delete_server_group  (DELETE — HMAC-confirmed)
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


class ListServerGroupsInput(BaseModel):
    """Inputs for listing ZPA server groups."""

    search: Annotated[
        Optional[str], Field(default=None, description="Server-side substring match on `name`.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None
    page: Annotated[Optional[int], Field(default=None, ge=1, description="Page number.")] = None
    page_size: Annotated[
        Optional[int], Field(default=None, ge=1, le=500, description="Items per page.")
    ] = None


class GetServerGroupInput(BaseModel):
    """Inputs for getting one ZPA server group."""

    group_id: Annotated[str, Field(description="Server group ID (string, even if numeric).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class CreateServerGroupInput(BaseModel):
    """Inputs for creating a ZPA server group."""

    name: Annotated[str, Field(description="Display name for the server group.")]
    app_connector_group_ids: Annotated[
        list[str],
        Field(
            description=(
                "REQUIRED, non-empty. App Connector Group IDs to bind. Discover via "
                "`zpa_list_app_connector_groups` — never invent IDs."
            )
        ),
    ]
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    enabled: Annotated[bool, Field(default=True, description="Whether the group is enabled.")] = (
        True
    )
    server_ids: Annotated[
        Optional[list[str]],
        Field(
            default=None,
            description="Application Server IDs. Required when dynamic_discovery=False.",
        ),
    ] = None
    ip_anchored: Annotated[
        Optional[bool], Field(default=None, description="Whether the group is IP anchored.")
    ] = None
    dynamic_discovery: Annotated[
        bool,
        Field(
            default=True,
            description=(
                "Default True (connector resolves backends from app-segment domains). "
                "Set False only to pin to explicit server_ids."
            ),
        ),
    ] = True
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class UpdateServerGroupInput(BaseModel):
    """Inputs for updating a ZPA server group (partial)."""

    group_id: Annotated[str, Field(description="Server group ID (string, even if numeric).")]
    name: Annotated[Optional[str], Field(default=None, description="New display name.")] = None
    description: Annotated[Optional[str], Field(default=None, description="New description.")] = (
        None
    )
    enabled: Annotated[Optional[bool], Field(default=None, description="Enable/disable.")] = None
    app_connector_group_ids: Annotated[
        Optional[list[str]],
        Field(default=None, description="Replace connector group IDs. Empty list is rejected."),
    ] = None
    server_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Replace Application Server IDs.")
    ] = None
    ip_anchored: Annotated[
        Optional[bool], Field(default=None, description="Whether the group is IP anchored.")
    ] = None
    dynamic_discovery: Annotated[
        Optional[bool], Field(default=None, description="Omit to preserve current value.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class DeleteServerGroupInput(BaseModel):
    """Inputs for deleting a ZPA server group (destructive)."""

    group_id: Annotated[str, Field(description="Server group ID (string, even if numeric).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


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
    service="zpa",
    toolset="zpa_server_groups",
    input_model=ListServerGroupsInput,
    is_list=True,
)
def zpa_list_server_groups(args: ListServerGroupsInput) -> list[dict[str, Any]]:
    """List ZPA server groups (read-only)."""
    client = get_zscaler_client(service="zpa")
    qp: dict[str, Any] = {"microtenant_id": args.microtenant_id}
    if args.search:
        qp["search"] = args.search
    if args.page is not None:
        qp["page"] = str(args.page)
    if args.page_size is not None:
        qp["page_size"] = str(args.page_size)
    groups, _, err = client.zpa.server_groups.list_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list server groups: {err}")
    return shape_many([g.as_dict() for g in (groups or [])])


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_server_groups",
    input_model=GetServerGroupInput,
    is_list=False,
)
def zpa_get_server_group(args: GetServerGroupInput) -> dict[str, Any]:
    """Get one ZPA server group (read-only)."""
    if not args.group_id:
        raise ValueError("group_id is required")
    client = get_zscaler_client(service="zpa")
    group, _, err = client.zpa.server_groups.get_group(
        args.group_id, query_params={"microtenant_id": args.microtenant_id}
    )
    if err:
        raise RuntimeError(f"Failed to get server group {args.group_id}: {err}")
    return shape_one(group.as_dict())


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_server_groups",
    input_model=CreateServerGroupInput,
    is_list=False,
)
def zpa_create_server_group(args: CreateServerGroupInput) -> dict[str, Any]:
    """Create a ZPA server group (write).

    Gated by HMAC write-confirmation and `--write-tools`. Requires at least one
    App Connector Group; dynamic_discovery=False requires server_ids.
    """
    if not args.name:
        raise ValueError("name is required")
    if not args.app_connector_group_ids:
        raise ValueError(
            "app_connector_group_ids is required and must contain at least one ID. "
            "Use zpa_list_app_connector_groups to discover existing groups."
        )
    if args.dynamic_discovery is False and not args.server_ids:
        raise ValueError("dynamic_discovery=False requires server_ids to be a non-empty list.")

    client = get_zscaler_client(service="zpa")
    body: dict[str, Any] = {
        "name": args.name,
        "enabled": args.enabled,
        "app_connector_group_ids": args.app_connector_group_ids,
        "dynamic_discovery": args.dynamic_discovery,
    }
    if args.description is not None:
        body["description"] = args.description
    if args.server_ids:
        body["server_ids"] = args.server_ids
    if args.ip_anchored is not None:
        body["ip_anchored"] = args.ip_anchored
    if args.microtenant_id:
        body["microtenant_id"] = args.microtenant_id

    created, _, err = client.zpa.server_groups.add_group(**body)
    if err:
        raise RuntimeError(f"Failed to create server group: {err}")
    return shape_one(created.as_dict())


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_server_groups",
    input_model=UpdateServerGroupInput,
    is_list=False,
)
def zpa_update_server_group(args: UpdateServerGroupInput) -> dict[str, Any]:
    """Update a ZPA server group (write).

    Partial update. Gated by HMAC write-confirmation and `--write-tools`.
    `app_connector_group_ids=[]` is rejected; dynamic_discovery=False requires
    server_ids be supplied here or already present on the group.
    """
    if not args.group_id:
        raise ValueError("group_id is required for update")
    if args.app_connector_group_ids is not None and len(args.app_connector_group_ids) == 0:
        raise ValueError(
            "app_connector_group_ids cannot be set to an empty list — omit it to "
            "preserve the existing binding."
        )

    client = get_zscaler_client(service="zpa")
    api = client.zpa.server_groups

    if args.dynamic_discovery is False and not args.server_ids:
        existing, _, err = api.get_group(
            args.group_id, query_params={"microtenant_id": args.microtenant_id}
        )
        if err:
            raise RuntimeError(
                f"Failed to fetch server group {args.group_id} for validation: {err}"
            )
        existing_servers = (
            getattr(existing, "servers", None) or existing.as_dict().get("servers") or []
        )
        if not existing_servers:
            raise ValueError(
                "dynamic_discovery=False requires server_ids to be non-empty (the "
                "existing group has no servers bound)."
            )

    body: dict[str, Any] = {}
    if args.name is not None:
        body["name"] = args.name
    if args.description is not None:
        body["description"] = args.description
    if args.enabled is not None:
        body["enabled"] = args.enabled
    if args.app_connector_group_ids is not None:
        body["app_connector_group_ids"] = args.app_connector_group_ids
    if args.server_ids is not None:
        body["server_ids"] = args.server_ids
    if args.ip_anchored is not None:
        body["ip_anchored"] = args.ip_anchored
    if args.dynamic_discovery is not None:
        body["dynamic_discovery"] = args.dynamic_discovery
    if args.microtenant_id:
        body["microtenant_id"] = args.microtenant_id

    updated, _, err = api.update_group(args.group_id, **body)
    if err:
        raise RuntimeError(f"Failed to update server group {args.group_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_server_groups",
    input_model=DeleteServerGroupInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_server_group(args: DeleteServerGroupInput) -> dict[str, Any]:
    """Delete a ZPA server group (destructive write).

    Cannot be undone. Gated by HMAC write-confirmation and `--write-tools`.
    """
    if not args.group_id:
        raise ValueError("group_id is required for delete")
    client = get_zscaler_client(service="zpa")
    _, _, err = client.zpa.server_groups.delete_group(
        args.group_id, microtenant_id=args.microtenant_id
    )
    if err:
        raise RuntimeError(f"Failed to delete server group {args.group_id}: {err}")
    return OperationResult(
        success=True, message=f"Server group {args.group_id} deleted successfully."
    ).model_dump()
