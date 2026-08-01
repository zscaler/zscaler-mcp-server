"""ZPA app connector groups — agent-first v2 CRUD tools.

Mirrors v1's ``zscaler_mcp/tools/zpa/app_connector_groups.py``. The create/update
tools resolve the tenant's standard "Connector" enrollment certificate
automatically when none is supplied (the ZPA API requires one on create).

    zpa_list_app_connector_groups   (READ)
    zpa_get_app_connector_group     (READ)
    zpa_create_app_connector_group  (CREATE)
    zpa_update_app_connector_group  (UPDATE)
    zpa_delete_app_connector_group  (DELETE — HMAC-confirmed)
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.zpa_helpers import normalize_iso_country_code, resolve_enrollment_cert_id
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, shape_many, shape_one

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListConnectorGroupsInput(BaseModel):
    """Inputs for listing ZPA app connector groups."""

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


class GetConnectorGroupInput(BaseModel):
    """Inputs for getting one ZPA app connector group."""

    group_id: Annotated[str, Field(description="Connector group ID (string, even if numeric).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class CreateConnectorGroupInput(BaseModel):
    """Inputs for creating a ZPA app connector group."""

    name: Annotated[str, Field(description="Display name for the connector group.")]
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    enabled: Annotated[bool, Field(default=True, description="Whether the group is enabled.")] = (
        True
    )
    latitude: Annotated[Optional[str], Field(default=None, description="Latitude coordinate.")] = (
        None
    )
    longitude: Annotated[
        Optional[str], Field(default=None, description="Longitude coordinate.")
    ] = None
    location: Annotated[Optional[str], Field(default=None, description="Location name.")] = None
    city_country: Annotated[Optional[str], Field(default=None, description="City and country.")] = (
        None
    )
    country_code: Annotated[
        Optional[str],
        Field(default=None, description="ISO alpha-2 country code (e.g. 'CA', 'US')."),
    ] = None
    dns_query_type: Annotated[Optional[str], Field(default=None, description="DNS query type.")] = (
        None
    )
    override_version_profile: Annotated[
        Optional[bool], Field(default=None, description="Override version profile.")
    ] = None
    server_group_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Server group IDs.")
    ] = None
    connector_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Connector IDs.")
    ] = None
    lss_app_connector_group: Annotated[
        Optional[bool], Field(default=None, description="Whether this is an LSS connector group.")
    ] = None
    upgrade_day: Annotated[Optional[str], Field(default=None, description="Upgrade day.")] = None
    upgrade_time_in_secs: Annotated[
        Optional[str], Field(default=None, description="Upgrade time in seconds.")
    ] = None
    version_profile: Annotated[
        Optional[str], Field(default=None, description="Version profile.")
    ] = None
    enrollment_cert_id: Annotated[
        Optional[str],
        Field(
            default=None, description="Enrollment cert ID (auto-resolves 'Connector' if omitted)."
        ),
    ] = None
    enrollment_cert_name: Annotated[
        Optional[str],
        Field(default=None, description="Enrollment cert name to look up (default 'Connector')."),
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class UpdateConnectorGroupInput(BaseModel):
    """Inputs for updating a ZPA app connector group (partial)."""

    group_id: Annotated[str, Field(description="Connector group ID (string, even if numeric).")]
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
    dns_query_type: Annotated[Optional[str], Field(default=None, description="DNS query type.")] = (
        None
    )
    override_version_profile: Annotated[
        Optional[bool], Field(default=None, description="Override version profile.")
    ] = None
    server_group_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Server group IDs.")
    ] = None
    connector_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Connector IDs.")
    ] = None
    lss_app_connector_group: Annotated[
        Optional[bool], Field(default=None, description="Whether this is an LSS connector group.")
    ] = None
    upgrade_day: Annotated[Optional[str], Field(default=None, description="Upgrade day.")] = None
    upgrade_time_in_secs: Annotated[
        Optional[str], Field(default=None, description="Upgrade time in seconds.")
    ] = None
    version_profile: Annotated[
        Optional[str], Field(default=None, description="Version profile.")
    ] = None
    enrollment_cert_id: Annotated[
        Optional[str], Field(default=None, description="Rotate to this enrollment cert ID.")
    ] = None
    enrollment_cert_name: Annotated[
        Optional[str], Field(default=None, description="Rotate to this enrollment cert by name.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class DeleteConnectorGroupInput(BaseModel):
    """Inputs for deleting a ZPA app connector group (destructive)."""

    group_id: Annotated[str, Field(description="Connector group ID (string, even if numeric).")]
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
    toolset="zpa_app_connector_groups",
    input_model=ListConnectorGroupsInput,
    is_list=True,
)
def zpa_list_app_connector_groups(args: ListConnectorGroupsInput) -> list[dict[str, Any]]:
    """List ZPA app connector groups (read-only)."""
    client = get_zscaler_client(service="zpa")
    qp: dict[str, Any] = {"microtenant_id": args.microtenant_id}
    if args.search:
        qp["search"] = args.search
    if args.page is not None:
        qp["page"] = str(args.page)
    if args.page_size is not None:
        qp["page_size"] = str(args.page_size)
    groups, _, err = client.zpa.app_connector_groups.list_connector_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list app connector groups: {err}")
    return shape_many([g.as_dict() for g in (groups or [])])


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_app_connector_groups",
    input_model=GetConnectorGroupInput,
    is_list=False,
)
def zpa_get_app_connector_group(args: GetConnectorGroupInput) -> dict[str, Any]:
    """Get one ZPA app connector group (read-only)."""
    if not args.group_id:
        raise ValueError("group_id is required")
    client = get_zscaler_client(service="zpa")
    group, _, err = client.zpa.app_connector_groups.get_connector_group(
        args.group_id, query_params={"microtenant_id": args.microtenant_id}
    )
    if err:
        raise RuntimeError(f"Failed to get app connector group {args.group_id}: {err}")
    return shape_one(group.as_dict())


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_app_connector_groups",
    input_model=CreateConnectorGroupInput,
    is_list=False,
)
def zpa_create_app_connector_group(args: CreateConnectorGroupInput) -> dict[str, Any]:
    """Create a ZPA app connector group (write).

    Requires `--write-tools`. Auto-resolves the
    tenant's standard 'Connector' enrollment certificate when none is supplied.
    """
    if not args.name:
        raise ValueError("name is required")
    client = get_zscaler_client(service="zpa")

    country_code = normalize_iso_country_code(args.country_code) if args.country_code else None
    resolved_cert_id = resolve_enrollment_cert_id(
        client,
        enrollment_cert_id=args.enrollment_cert_id,
        enrollment_cert_name=args.enrollment_cert_name,
    )

    body: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "enabled": args.enabled,
        "latitude": args.latitude,
        "longitude": args.longitude,
        "location": args.location,
        "city_country": args.city_country,
        "country_code": country_code,
        "dns_query_type": args.dns_query_type,
        "override_version_profile": args.override_version_profile,
        "server_group_ids": args.server_group_ids or [],
        "connector_ids": args.connector_ids or [],
        "lss_app_connector_group": args.lss_app_connector_group,
        "upgrade_day": args.upgrade_day,
        "upgrade_time_in_secs": args.upgrade_time_in_secs,
        "version_profile": args.version_profile,
        "enrollment_cert_id": resolved_cert_id,
    }
    if args.microtenant_id:
        body["microtenant_id"] = args.microtenant_id

    created, _, err = client.zpa.app_connector_groups.add_connector_group(**body)
    if err:
        raise RuntimeError(f"Failed to create app connector group: {err}")
    return shape_one(created.as_dict())


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_app_connector_groups",
    input_model=UpdateConnectorGroupInput,
    is_list=False,
)
def zpa_update_app_connector_group(args: UpdateConnectorGroupInput) -> dict[str, Any]:
    """Update a ZPA app connector group (write).

    Requires `--write-tools`. The enrollment
    certificate is preserved unless enrollment_cert_id/name is explicitly passed.
    """
    if not args.group_id:
        raise ValueError("group_id is required for update")
    client = get_zscaler_client(service="zpa")

    country_code = normalize_iso_country_code(args.country_code) if args.country_code else None
    resolved_cert_id: Optional[str] = None
    if args.enrollment_cert_id or args.enrollment_cert_name:
        resolved_cert_id = resolve_enrollment_cert_id(
            client,
            enrollment_cert_id=args.enrollment_cert_id,
            enrollment_cert_name=args.enrollment_cert_name,
        )

    body: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "enabled": args.enabled,
        "latitude": args.latitude,
        "longitude": args.longitude,
        "location": args.location,
        "city_country": args.city_country,
        "country_code": country_code,
        "dns_query_type": args.dns_query_type,
        "override_version_profile": args.override_version_profile,
        "server_group_ids": args.server_group_ids or [],
        "connector_ids": args.connector_ids or [],
        "lss_app_connector_group": args.lss_app_connector_group,
        "upgrade_day": args.upgrade_day,
        "upgrade_time_in_secs": args.upgrade_time_in_secs,
        "version_profile": args.version_profile,
    }
    if resolved_cert_id is not None:
        body["enrollment_cert_id"] = resolved_cert_id
    if args.microtenant_id:
        body["microtenant_id"] = args.microtenant_id

    updated, _, err = client.zpa.app_connector_groups.update_connector_group(args.group_id, **body)
    if err:
        raise RuntimeError(f"Failed to update app connector group {args.group_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_app_connector_groups",
    input_model=DeleteConnectorGroupInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_app_connector_group(args: DeleteConnectorGroupInput) -> dict[str, Any]:
    """Delete a ZPA app connector group (destructive write).

    Cannot be undone.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    if not args.group_id:
        raise ValueError("group_id is required for delete")
    client = get_zscaler_client(service="zpa")
    _, _, err = client.zpa.app_connector_groups.delete_connector_group(
        args.group_id, microtenant_id=args.microtenant_id
    )
    if err:
        raise RuntimeError(f"Failed to delete app connector group {args.group_id}: {err}")
    return OperationResult(
        success=True, message=f"App connector group {args.group_id} deleted successfully."
    ).model_dump()
