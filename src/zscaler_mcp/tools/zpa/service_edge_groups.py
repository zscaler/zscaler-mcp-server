"""ZPA service edge groups — agent-first v2 CRUD tools.

Mirrors v1's ``zscaler_mcp/tools/zpa/service_edge_groups.py``.

    zpa_list_service_edge_groups   (READ)
    zpa_get_service_edge_group     (READ)
    zpa_create_service_edge_group  (CREATE)
    zpa_update_service_edge_group  (UPDATE)
    zpa_delete_service_edge_group  (DELETE — HMAC-confirmed)
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.zpa_helpers import normalize_iso_country_code
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, shape_many, shape_one

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListServiceEdgeGroupsInput(BaseModel):
    """Inputs for listing ZPA service edge groups."""

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


class GetServiceEdgeGroupInput(BaseModel):
    """Inputs for getting one ZPA service edge group."""

    group_id: Annotated[str, Field(description="Service edge group ID (string, even if numeric).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class CreateServiceEdgeGroupInput(BaseModel):
    """Inputs for creating a ZPA service edge group."""

    name: Annotated[str, Field(description="Display name for the service edge group.")]
    latitude: Annotated[str, Field(description="Latitude coordinate (required).")]
    longitude: Annotated[str, Field(description="Longitude coordinate (required).")]
    location: Annotated[str, Field(description="Location name (required).")]
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    enabled: Annotated[bool, Field(default=True, description="Whether the group is enabled.")] = (
        True
    )
    city_country: Annotated[Optional[str], Field(default=None, description="City and country.")] = (
        None
    )
    country_code: Annotated[
        Optional[str], Field(default=None, description="ISO alpha-2 country code (e.g. 'CA').")
    ] = None
    is_public: Annotated[Optional[bool], Field(default=None, description="Whether public.")] = None
    override_version_profile: Annotated[
        Optional[bool], Field(default=None, description="Override version profile.")
    ] = None
    version_profile_name: Annotated[
        Optional[str], Field(default=None, description="Version profile name.")
    ] = None
    version_profile_id: Annotated[
        Optional[str], Field(default=None, description="Version profile ID.")
    ] = None
    service_edge_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Service edge IDs.")
    ] = None
    trusted_network_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Trusted network IDs.")
    ] = None
    grace_distance_enabled: Annotated[
        Optional[bool], Field(default=None, description="Grace distance enabled.")
    ] = None
    grace_distance_value: Annotated[
        Optional[int], Field(default=None, description="Grace distance value.")
    ] = None
    grace_distance_value_unit: Annotated[
        Optional[str], Field(default=None, description="Grace distance value unit.")
    ] = None
    upgrade_day: Annotated[Optional[str], Field(default=None, description="Upgrade day.")] = None
    upgrade_time_in_secs: Annotated[
        Optional[str], Field(default=None, description="Upgrade time in seconds.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class UpdateServiceEdgeGroupInput(BaseModel):
    """Inputs for updating a ZPA service edge group (partial)."""

    group_id: Annotated[str, Field(description="Service edge group ID (string, even if numeric).")]
    name: Annotated[Optional[str], Field(default=None, description="New display name.")] = None
    description: Annotated[Optional[str], Field(default=None, description="New description.")] = (
        None
    )
    enabled: Annotated[Optional[bool], Field(default=None, description="Enable/disable.")] = None
    latitude: Annotated[Optional[str], Field(default=None, description="Latitude.")] = None
    longitude: Annotated[Optional[str], Field(default=None, description="Longitude.")] = None
    location: Annotated[Optional[str], Field(default=None, description="Location name.")] = None
    city_country: Annotated[Optional[str], Field(default=None, description="City and country.")] = (
        None
    )
    country_code: Annotated[
        Optional[str], Field(default=None, description="ISO alpha-2 country code.")
    ] = None
    is_public: Annotated[Optional[bool], Field(default=None, description="Whether public.")] = None
    override_version_profile: Annotated[
        Optional[bool], Field(default=None, description="Override version profile.")
    ] = None
    version_profile_name: Annotated[
        Optional[str], Field(default=None, description="Version profile name.")
    ] = None
    version_profile_id: Annotated[
        Optional[str], Field(default=None, description="Version profile ID.")
    ] = None
    service_edge_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Service edge IDs.")
    ] = None
    trusted_network_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Trusted network IDs.")
    ] = None
    grace_distance_enabled: Annotated[
        Optional[bool], Field(default=None, description="Grace distance enabled.")
    ] = None
    grace_distance_value: Annotated[
        Optional[int], Field(default=None, description="Grace distance value.")
    ] = None
    grace_distance_value_unit: Annotated[
        Optional[str], Field(default=None, description="Grace distance value unit.")
    ] = None
    upgrade_day: Annotated[Optional[str], Field(default=None, description="Upgrade day.")] = None
    upgrade_time_in_secs: Annotated[
        Optional[str], Field(default=None, description="Upgrade time in seconds.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class DeleteServiceEdgeGroupInput(BaseModel):
    """Inputs for deleting a ZPA service edge group (destructive)."""

    group_id: Annotated[str, Field(description="Service edge group ID (string, even if numeric).")]
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


def _build_body(args: Any) -> dict[str, Any]:
    country_code = normalize_iso_country_code(args.country_code) if args.country_code else None
    body: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "enabled": args.enabled,
        "latitude": args.latitude,
        "longitude": args.longitude,
        "location": args.location,
        "city_country": args.city_country,
        "country_code": country_code,
        "is_public": args.is_public,
        "override_version_profile": args.override_version_profile,
        "version_profile_name": args.version_profile_name,
        "version_profile_id": args.version_profile_id,
        "grace_distance_enabled": args.grace_distance_enabled,
        "grace_distance_value": args.grace_distance_value,
        "grace_distance_value_unit": args.grace_distance_value_unit,
        "upgrade_day": args.upgrade_day,
        "upgrade_time_in_secs": args.upgrade_time_in_secs,
    }
    if args.microtenant_id:
        body["microtenant_id"] = args.microtenant_id
    if args.trusted_network_ids:
        body["trusted_network_ids"] = args.trusted_network_ids
    if args.service_edge_ids:
        body["service_edge_ids"] = args.service_edge_ids
    return body


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_service_edge_groups",
    input_model=ListServiceEdgeGroupsInput,
    is_list=True,
)
def zpa_list_service_edge_groups(args: ListServiceEdgeGroupsInput) -> list[dict[str, Any]]:
    """List ZPA service edge groups (read-only)."""
    client = get_zscaler_client(service="zpa")
    qp: dict[str, Any] = {"microtenant_id": args.microtenant_id}
    if args.search:
        qp["search"] = args.search
    if args.page is not None:
        qp["page"] = str(args.page)
    if args.page_size is not None:
        qp["page_size"] = str(args.page_size)
    groups, _, err = client.zpa.service_edge_group.list_service_edge_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list service edge groups: {err}")
    return shape_many([g.as_dict() for g in (groups or [])])


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_service_edge_groups",
    input_model=GetServiceEdgeGroupInput,
    is_list=False,
)
def zpa_get_service_edge_group(args: GetServiceEdgeGroupInput) -> dict[str, Any]:
    """Get one ZPA service edge group (read-only)."""
    if not args.group_id:
        raise ValueError("group_id is required")
    client = get_zscaler_client(service="zpa")
    group, _, err = client.zpa.service_edge_group.get_service_edge_group(
        args.group_id, query_params={"microtenant_id": args.microtenant_id}
    )
    if err:
        raise RuntimeError(f"Failed to get service edge group {args.group_id}: {err}")
    return shape_one(group.as_dict())


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_service_edge_groups",
    input_model=CreateServiceEdgeGroupInput,
    is_list=False,
)
def zpa_create_service_edge_group(args: CreateServiceEdgeGroupInput) -> dict[str, Any]:
    """Create a ZPA service edge group (write).

    Requires `--write-tools`, plus name,
    latitude, longitude, and location.
    """
    if not all([args.name, args.latitude, args.longitude, args.location]):
        raise ValueError("name, latitude, longitude, and location are required")
    client = get_zscaler_client(service="zpa")
    body = _build_body(args)
    created, _, err = client.zpa.service_edge_group.add_service_edge_group(**body)
    if err:
        raise RuntimeError(f"Failed to create service edge group: {err}")
    return shape_one(created.as_dict())


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_service_edge_groups",
    input_model=UpdateServiceEdgeGroupInput,
    is_list=False,
)
def zpa_update_service_edge_group(args: UpdateServiceEdgeGroupInput) -> dict[str, Any]:
    """Update a ZPA service edge group (write).

    Requires `--write-tools`.
    """
    if not args.group_id:
        raise ValueError("group_id is required for update")
    client = get_zscaler_client(service="zpa")
    body = _build_body(args)
    updated, _, err = client.zpa.service_edge_group.update_service_edge_group(args.group_id, **body)
    if err:
        raise RuntimeError(f"Failed to update service edge group {args.group_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_service_edge_groups",
    input_model=DeleteServiceEdgeGroupInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_service_edge_group(args: DeleteServiceEdgeGroupInput) -> dict[str, Any]:
    """Delete a ZPA service edge group (destructive write).

    Cannot be undone.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    if not args.group_id:
        raise ValueError("group_id is required for delete")
    client = get_zscaler_client(service="zpa")
    _, _, err = client.zpa.service_edge_group.delete_service_edge_group(
        args.group_id, microtenant_id=args.microtenant_id
    )
    if err:
        raise RuntimeError(f"Failed to delete service edge group {args.group_id}: {err}")
    return OperationResult(
        success=True, message=f"Service edge group {args.group_id} deleted successfully."
    ).model_dump()
