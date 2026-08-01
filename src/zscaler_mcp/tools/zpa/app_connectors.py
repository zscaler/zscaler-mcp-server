"""ZPA App Connectors — agent-first v2 tools.

Mirrors v1's ``app_connectors.py``. Connectors are *enrolled* (a connector
self-registers using a provisioning key) rather than created, so there is no
create tool — only list / get / update / delete / bulk-delete.

    zpa_list_app_connectors          (READ)
    zpa_get_app_connector            (READ)
    zpa_update_app_connector         (UPDATE)
    zpa_delete_app_connector         (DELETE — HMAC-confirmed)
    zpa_bulk_delete_app_connectors   (DELETE — HMAC-confirmed)
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

_CONN_GROUP = "app_connector_group_id"


class ListInput(BaseModel):
    """Inputs for listing app connectors."""

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


class GetConnectorInput(BaseModel):
    """Inputs for getting one app connector."""

    connector_id: Annotated[str, Field(description="App connector ID (string, even if numeric).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class UpdateConnectorInput(BaseModel):
    """Inputs for updating an app connector (partial)."""

    connector_id: Annotated[str, Field(description="App connector ID (string, even if numeric).")]
    name: Annotated[Optional[str], Field(default=None, description="New display name.")] = None
    description: Annotated[Optional[str], Field(default=None, description="New description.")] = (
        None
    )
    enabled: Annotated[
        Optional[bool], Field(default=None, description="Enable/disable the connector.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class DeleteConnectorInput(BaseModel):
    """Inputs for deleting one app connector (destructive)."""

    connector_id: Annotated[str, Field(description="App connector ID (string, even if numeric).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class BulkDeleteConnectorsInput(BaseModel):
    """Inputs for bulk-deleting app connectors (destructive)."""

    connector_ids: Annotated[list[str], Field(description="App connector IDs to delete.")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_connectors",
    input_model=ListInput,
    is_list=True,
)
def zpa_list_app_connectors(args: ListInput) -> list[dict[str, Any]]:
    """List ZPA app connectors with health/status (read-only)."""
    client = get_zscaler_client(service="zpa")
    qp = query_params(
        search=args.search,
        page=args.page,
        page_size=args.page_size,
        microtenant_id=args.microtenant_id,
    )
    connectors, _, err = client.zpa.app_connectors.list_connectors(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list app connectors: {err}")
    return shape_many([c.as_dict() for c in (connectors or [])])


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_connectors",
    input_model=GetConnectorInput,
    is_list=False,
)
def zpa_get_app_connector(args: GetConnectorInput) -> dict[str, Any]:
    """Get one ZPA app connector by ID (read-only)."""
    if not args.connector_id:
        raise ValueError("connector_id is required")
    client = get_zscaler_client(service="zpa")
    qp: dict[str, Any] = {}
    if args.microtenant_id:
        qp["microtenant_id"] = args.microtenant_id
    connector, _, err = client.zpa.app_connectors.get_connector(args.connector_id, query_params=qp)
    if err:
        raise RuntimeError(f"Failed to get app connector {args.connector_id}: {err}")
    return shape_one(connector.as_dict())


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_connectors",
    input_model=UpdateConnectorInput,
    is_list=False,
)
def zpa_update_app_connector(args: UpdateConnectorInput) -> dict[str, Any]:
    """Update a ZPA app connector (enable/disable, rename). Requires `--write-tools`."""
    if not args.connector_id:
        raise ValueError("connector_id is required")
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
    updated, _, err = client.zpa.app_connectors.update_connector(args.connector_id, **body)
    if err:
        raise RuntimeError(f"Failed to update app connector {args.connector_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_connectors",
    input_model=DeleteConnectorInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_app_connector(args: DeleteConnectorInput) -> dict[str, Any]:
    """Delete a ZPA app connector (destructive write). Must be re-provisioned to reconnect.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    if not args.connector_id:
        raise ValueError("connector_id is required")
    client = get_zscaler_client(service="zpa")
    _, _, err = client.zpa.app_connectors.delete_connector(
        args.connector_id, microtenant_id=args.microtenant_id
    )
    if err:
        raise RuntimeError(f"Failed to delete app connector {args.connector_id}: {err}")
    return OperationResult(
        success=True, message=f"App connector {args.connector_id} deleted successfully."
    ).model_dump()


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_connectors",
    input_model=BulkDeleteConnectorsInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_bulk_delete_app_connectors(args: BulkDeleteConnectorsInput) -> dict[str, Any]:
    """Bulk-delete ZPA app connectors (destructive write). Each must be re-provisioned to reconnect.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    if not args.connector_ids:
        raise ValueError("connector_ids is required and must not be empty")
    client = get_zscaler_client(service="zpa")
    _, _, err = client.zpa.app_connectors.bulk_delete_connectors(
        args.connector_ids, microtenant_id=args.microtenant_id
    )
    if err:
        raise RuntimeError(f"Failed to bulk delete app connectors: {err}")
    return OperationResult(
        success=True, message=f"Deleted {len(args.connector_ids)} app connectors successfully."
    ).model_dump()
