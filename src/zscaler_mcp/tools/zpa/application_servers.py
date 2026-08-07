"""ZPA application servers — agent-first v2 CRUD tools.

Mirrors v1's ``zscaler_mcp/tools/zpa/application_servers.py``. An application
server is a backend host (IP/FQDN) referenced by ZPA server groups.

    zpa_list_application_servers   (READ)
    zpa_get_application_server     (READ)
    zpa_create_application_server  (CREATE)
    zpa_update_application_server  (UPDATE)
    zpa_delete_application_server  (DELETE — HMAC-confirmed)
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


class ListServersInput(BaseModel):
    """Inputs for listing ZPA application servers."""

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


class GetServerInput(BaseModel):
    """Inputs for getting one ZPA application server."""

    server_id: Annotated[str, Field(description="Application server ID (string, even if numeric).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class CreateServerInput(BaseModel):
    """Inputs for creating a ZPA application server."""

    name: Annotated[str, Field(description="Display name for the application server.")]
    address: Annotated[str, Field(description="Domain or IP address of the server.")]
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    enabled: Annotated[bool, Field(default=True, description="Whether the server is enabled.")] = (
        True
    )
    app_server_group_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Server group IDs to associate.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class UpdateServerInput(BaseModel):
    """Inputs for updating a ZPA application server (partial)."""

    server_id: Annotated[str, Field(description="Application server ID (string, even if numeric).")]
    name: Annotated[Optional[str], Field(default=None, description="New display name.")] = None
    address: Annotated[Optional[str], Field(default=None, description="New domain/IP.")] = None
    description: Annotated[Optional[str], Field(default=None, description="New description.")] = (
        None
    )
    enabled: Annotated[Optional[bool], Field(default=None, description="Enable/disable.")] = None
    app_server_group_ids: Annotated[
        Optional[list[str]], Field(default=None, description="New server group IDs.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class DeleteServerInput(BaseModel):
    """Inputs for deleting a ZPA application server (destructive)."""

    server_id: Annotated[str, Field(description="Application server ID (string, even if numeric).")]
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
    toolset="zpa_application_servers",
    input_model=ListServersInput,
    is_list=True,
)
def zpa_list_application_servers(args: ListServersInput) -> list[dict[str, Any]]:
    """List ZPA application servers (read-only)."""
    client = get_zscaler_client(service="zpa")
    qp: dict[str, Any] = {"microtenant_id": args.microtenant_id}
    if args.search:
        qp["search"] = args.search
    if args.page is not None:
        qp["page"] = str(args.page)
    if args.page_size is not None:
        qp["page_size"] = str(args.page_size)
    servers, _, err = client.zpa.servers.list_servers(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list application servers: {err}")
    return shape_many([s.as_dict() for s in (servers or [])])


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_application_servers",
    input_model=GetServerInput,
    is_list=False,
)
def zpa_get_application_server(args: GetServerInput) -> dict[str, Any]:
    """Get one ZPA application server (read-only)."""
    if not args.server_id:
        raise ValueError("server_id is required")
    client = get_zscaler_client(service="zpa")
    result, _, err = client.zpa.servers.get_server(
        args.server_id, query_params={"microtenant_id": args.microtenant_id}
    )
    if err:
        raise RuntimeError(f"Failed to get application server {args.server_id}: {err}")
    return shape_one(result.as_dict())


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_application_servers",
    input_model=CreateServerInput,
    is_list=False,
)
def zpa_create_application_server(args: CreateServerInput) -> dict[str, Any]:
    """Create a ZPA application server (write).

    Requires `--write-tools`.
    """
    if not args.name or not args.address:
        raise ValueError("name and address are required")
    client = get_zscaler_client(service="zpa")
    payload: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "address": args.address,
        "enabled": args.enabled,
        "app_server_group_ids": args.app_server_group_ids,
    }
    if args.microtenant_id:
        payload["microtenant_id"] = args.microtenant_id
    created, _, err = client.zpa.servers.add_server(**payload)
    if err:
        raise RuntimeError(f"Failed to create application server: {err}")
    return shape_one(created.as_dict())


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_application_servers",
    input_model=UpdateServerInput,
    is_list=False,
)
def zpa_update_application_server(args: UpdateServerInput) -> dict[str, Any]:
    """Update a ZPA application server (write).

    Requires `--write-tools`. Only the provided
    fields are sent.
    """
    if not args.server_id:
        raise ValueError("server_id is required for update")
    client = get_zscaler_client(service="zpa")
    payload: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "address": args.address,
        "enabled": args.enabled,
        "app_server_group_ids": args.app_server_group_ids,
    }
    if args.microtenant_id:
        payload["microtenant_id"] = args.microtenant_id
    updated, _, err = client.zpa.servers.update_server(args.server_id, **payload)
    if err:
        raise RuntimeError(f"Failed to update application server {args.server_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_application_servers",
    input_model=DeleteServerInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_application_server(args: DeleteServerInput) -> dict[str, Any]:
    """Delete a ZPA application server (destructive write).

    Cannot be undone.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    if not args.server_id:
        raise ValueError("server_id is required for deletion")
    client = get_zscaler_client(service="zpa")
    _, _, err = client.zpa.servers.delete_server(args.server_id, microtenant_id=args.microtenant_id)
    if err:
        raise RuntimeError(f"Failed to delete application server {args.server_id}: {err}")
    return OperationResult(
        success=True, message=f"Application server {args.server_id} deleted successfully."
    ).model_dump()
