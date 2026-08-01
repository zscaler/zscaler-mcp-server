"""ZPA Service Edges — agent-first v2 tools.

Mirrors v1's ``service_edges.py``. Service edges (the cloud-hosted broker
instances themselves, distinct from their parent service edge groups) are
*enrolled* via a provisioning key rather than created, so there is no create
tool — only list / get / update / delete / bulk-delete.

    zpa_list_service_edges           (READ)
    zpa_get_service_edge             (READ)
    zpa_update_service_edge          (UPDATE)
    zpa_delete_service_edge          (DELETE — HMAC-confirmed)
    zpa_bulk_delete_service_edges    (DELETE — HMAC-confirmed)
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import shape_many, shape_one
from zscaler_mcp.tools.zpa._connector_common import (
    OperationResult,
    query_params,
)

_EDGE_GROUP = "service_edge_group_id"


class ListInput(BaseModel):
    """Inputs for listing service edges."""

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


class GetEdgeInput(BaseModel):
    """Inputs for getting one service edge."""

    service_edge_id: Annotated[str, Field(description="Service edge ID (string, even if numeric).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class UpdateEdgeInput(BaseModel):
    """Inputs for updating a service edge (partial)."""

    service_edge_id: Annotated[str, Field(description="Service edge ID (string, even if numeric).")]
    name: Annotated[Optional[str], Field(default=None, description="New display name.")] = None
    description: Annotated[Optional[str], Field(default=None, description="New description.")] = (
        None
    )
    enabled: Annotated[
        Optional[bool], Field(default=None, description="Enable/disable the edge.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class DeleteEdgeInput(BaseModel):
    """Inputs for deleting one service edge (destructive)."""

    service_edge_id: Annotated[str, Field(description="Service edge ID (string, even if numeric).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class BulkDeleteEdgesInput(BaseModel):
    """Inputs for bulk-deleting service edges (destructive)."""

    service_edge_ids: Annotated[list[str], Field(description="Service edge IDs to delete.")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_service_edge_groups",
    input_model=ListInput,
    is_list=True,
)
def zpa_list_service_edges(args: ListInput) -> list[dict[str, Any]]:
    """List individual ZPA Service Edges with health/status (read-only).

    Distinct from `zpa_list_service_edge_groups` (the parent group resource).
    """
    client = get_zscaler_client(service="zpa")
    qp = query_params(
        search=args.search,
        page=args.page,
        page_size=args.page_size,
        microtenant_id=args.microtenant_id,
    )
    edges, _, err = client.zpa.service_edges.list_service_edges(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list service edges: {err}")
    return shape_many([e.as_dict() for e in (edges or [])])


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_service_edge_groups",
    input_model=GetEdgeInput,
    is_list=False,
)
def zpa_get_service_edge(args: GetEdgeInput) -> dict[str, Any]:
    """Get one ZPA Service Edge by ID (read-only)."""
    if not args.service_edge_id:
        raise ValueError("service_edge_id is required")
    client = get_zscaler_client(service="zpa")
    kwargs: dict[str, Any] = {}
    if args.microtenant_id:
        kwargs["microtenant_id"] = args.microtenant_id
    edge = client.zpa.service_edges.get_service_edge(args.service_edge_id, **kwargs)
    if edge is None:
        raise RuntimeError(f"Failed to get service edge {args.service_edge_id}")
    return shape_one(edge.as_dict())


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_service_edge_groups",
    input_model=UpdateEdgeInput,
    is_list=False,
)
def zpa_update_service_edge(args: UpdateEdgeInput) -> dict[str, Any]:
    """Update a ZPA Service Edge (enable/disable, rename). Requires `--write-tools`."""
    if not args.service_edge_id:
        raise ValueError("service_edge_id is required")
    client = get_zscaler_client(service="zpa")
    body: dict[str, Any] = {}
    if args.name is not None:
        body["name"] = args.name
    if args.description is not None:
        body["description"] = args.description
    if args.enabled is not None:
        body["enabled"] = args.enabled
    if args.microtenant_id:
        body["microtenant_id"] = args.microtenant_id
    updated, _, err = client.zpa.service_edges.update_service_edge(args.service_edge_id, **body)
    if err:
        raise RuntimeError(f"Failed to update service edge {args.service_edge_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_service_edge_groups",
    input_model=DeleteEdgeInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_service_edge(args: DeleteEdgeInput) -> dict[str, Any]:
    """Delete a single ZPA Service Edge (destructive write). Must be re-provisioned to reconnect.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    if not args.service_edge_id:
        raise ValueError("service_edge_id is required")
    client = get_zscaler_client(service="zpa")
    _, _, err = client.zpa.service_edges.delete_service_edge(
        args.service_edge_id, microtenant_id=args.microtenant_id
    )
    if err:
        raise RuntimeError(f"Failed to delete service edge {args.service_edge_id}: {err}")
    return OperationResult(
        success=True, message=f"Service edge {args.service_edge_id} deleted successfully."
    ).model_dump()


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_service_edge_groups",
    input_model=BulkDeleteEdgesInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_bulk_delete_service_edges(args: BulkDeleteEdgesInput) -> dict[str, Any]:
    """Bulk-delete ZPA Service Edges (destructive write). Each must be re-provisioned to reconnect.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    if not args.service_edge_ids:
        raise ValueError("service_edge_ids is required and must not be empty")
    client = get_zscaler_client(service="zpa")
    _, _, err = client.zpa.service_edges.bulk_delete_service_edges(
        args.service_edge_ids, microtenant_id=args.microtenant_id
    )
    if err:
        raise RuntimeError(f"Failed to bulk delete service edges: {err}")
    return OperationResult(
        success=True, message=f"Deleted {len(args.service_edge_ids)} service edges successfully."
    ).model_dump()
