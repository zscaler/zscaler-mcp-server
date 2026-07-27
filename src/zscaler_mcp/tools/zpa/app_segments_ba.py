"""ZPA browser-access (BA) application segments — list, get, create, update, delete.

Mirrors v1's ``client.zpa.app_segments_ba_v2`` calls (``*_segment_ba``). A BA
segment is an application segment with browser-access (clientless) configuration;
the full records reuse the standard app-segment shape plus the BA app config
member count.
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


class ListBaSegmentsInput(BaseModel):
    """Inputs for listing ZPA browser-access application segments."""

    search: Annotated[
        Optional[str], Field(default=None, description="Server-side name substring match.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant scoping.")
    ] = None
    page: Annotated[Optional[int], Field(default=None, ge=1, description="Page number.")] = None
    page_size: Annotated[
        Optional[int], Field(default=None, ge=1, le=500, description="Per page.")
    ] = None


class GetBaSegmentInput(BaseModel):
    """Inputs for getting one ZPA browser-access application segment."""

    segment_id: Annotated[str, Field(description="BA segment ID (string).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant scoping.")
    ] = None


class CreateBaSegmentInput(BaseModel):
    """Inputs for creating a ZPA browser-access application segment."""

    name: Annotated[str, Field(description="Segment name.")]
    segment_group_id: Annotated[str, Field(description="Owning segment group ID.")]
    domain_names: Annotated[
        Optional[list[str]], Field(default=None, description="Domain names / FQDNs.")
    ] = None
    server_group_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Server group IDs.")
    ] = None
    tcp_port_ranges: Annotated[
        Optional[list[str]], Field(default=None, description="Flat TCP port list.")
    ] = None
    udp_port_ranges: Annotated[
        Optional[list[str]], Field(default=None, description="Flat UDP port list.")
    ] = None
    clientless_app_ids: Annotated[
        Optional[list[dict[str, Any]]],
        Field(default=None, description="Browser-access (clientless) app configs forwarded as-is."),
    ] = None
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    enabled: Annotated[bool, Field(default=True, description="Whether enabled.")] = True
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant scoping.")
    ] = None
    advanced: Annotated[
        Optional[dict[str, Any]],
        Field(default=None, description="Advanced SDK fields forwarded as-is."),
    ] = None


class UpdateBaSegmentInput(BaseModel):
    """Inputs for updating a ZPA browser-access application segment (partial)."""

    segment_id: Annotated[str, Field(description="BA segment ID (string).")]
    name: Annotated[Optional[str], Field(default=None, description="New name.")] = None
    segment_group_id: Annotated[
        Optional[str], Field(default=None, description="New segment group ID.")
    ] = None
    domain_names: Annotated[
        Optional[list[str]], Field(default=None, description="New domain names.")
    ] = None
    server_group_ids: Annotated[
        Optional[list[str]], Field(default=None, description="New server group IDs.")
    ] = None
    tcp_port_ranges: Annotated[
        Optional[list[str]], Field(default=None, description="New TCP ports.")
    ] = None
    udp_port_ranges: Annotated[
        Optional[list[str]], Field(default=None, description="New UDP ports.")
    ] = None
    clientless_app_ids: Annotated[
        Optional[list[dict[str, Any]]],
        Field(default=None, description="New clientless app configs."),
    ] = None
    description: Annotated[Optional[str], Field(default=None, description="New description.")] = (
        None
    )
    enabled: Annotated[Optional[bool], Field(default=None, description="Enable/disable.")] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant scoping.")
    ] = None
    advanced: Annotated[
        Optional[dict[str, Any]], Field(default=None, description="Advanced SDK fields.")
    ] = None


class DeleteBaSegmentInput(BaseModel):
    """Inputs for deleting a ZPA browser-access application segment (destructive)."""

    segment_id: Annotated[str, Field(description="BA segment ID (string).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant scoping.")
    ] = None


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)








def _build_body(args: Any) -> dict[str, Any]:
    body: dict[str, Any] = {}
    for field in (
        "name",
        "description",
        "enabled",
        "domain_names",
        "segment_group_id",
        "server_group_ids",
        "tcp_port_ranges",
        "udp_port_ranges",
        "clientless_app_ids",
    ):
        val = getattr(args, field, None)
        if val is not None:
            body[field] = val
    if getattr(args, "microtenant_id", None):
        body["microtenant_id"] = args.microtenant_id
    if getattr(args, "advanced", None):
        body.update(args.advanced)
    return body


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=ListBaSegmentsInput,
    is_list=True,
)
def zpa_list_application_segments_ba(args: ListBaSegmentsInput) -> list[dict[str, Any]]:
    """List ZPA browser-access (clientless) application segments."""
    client = get_zscaler_client(service="zpa")
    api = client.zpa.app_segments_ba_v2
    qp: dict[str, Any] = {"microtenant_id": args.microtenant_id}
    if args.search:
        qp["search"] = args.search
    if args.page is not None:
        qp["page"] = str(args.page)
    if args.page_size is not None:
        qp["page_size"] = str(args.page_size)
    segments, _, err = api.list_segments_ba(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list BA application segments: {err}")
    return shape_many([s.as_dict() for s in (segments or [])])


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=GetBaSegmentInput,
    is_list=False,
)
def zpa_get_application_segment_ba(args: GetBaSegmentInput) -> dict[str, Any]:
    """Get one ZPA browser-access application segment."""
    if not args.segment_id:
        raise ValueError("segment_id is required")
    client = get_zscaler_client(service="zpa")
    api = client.zpa.app_segments_ba_v2
    segment, _, err = api.get_segment_ba(
        args.segment_id, query_params={"microtenant_id": args.microtenant_id}
    )
    if err:
        raise RuntimeError(f"Failed to get BA application segment {args.segment_id}: {err}")
    return shape_one(segment.as_dict())


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=CreateBaSegmentInput,
    is_list=False,
)
def zpa_create_application_segment_ba(args: CreateBaSegmentInput) -> dict[str, Any]:
    """Create a ZPA browser-access application segment (write)."""
    if not args.name or not args.segment_group_id:
        raise ValueError("name and segment_group_id are required")
    client = get_zscaler_client(service="zpa")
    api = client.zpa.app_segments_ba_v2
    created, _, err = api.add_segment_ba(**_build_body(args))
    if err:
        raise RuntimeError(f"Failed to create BA application segment: {err}")
    return shape_one(created.as_dict())


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=UpdateBaSegmentInput,
    is_list=False,
)
def zpa_update_application_segment_ba(args: UpdateBaSegmentInput) -> dict[str, Any]:
    """Update a ZPA browser-access application segment (write). Only provided fields are sent."""
    if not args.segment_id:
        raise ValueError("segment_id is required for update")
    client = get_zscaler_client(service="zpa")
    api = client.zpa.app_segments_ba_v2
    updated, _, err = api.update_segment_ba(args.segment_id, **_build_body(args))
    if err:
        raise RuntimeError(f"Failed to update BA application segment {args.segment_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=DeleteBaSegmentInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_application_segment_ba(args: DeleteBaSegmentInput) -> dict[str, Any]:
    """Delete a ZPA browser-access application segment (destructive write). Cannot be undone."""
    if not args.segment_id:
        raise ValueError("segment_id is required for delete")
    client = get_zscaler_client(service="zpa")
    api = client.zpa.app_segments_ba_v2
    _, _, err = api.delete_segment_ba(args.segment_id, microtenant_id=args.microtenant_id)
    if err:
        raise RuntimeError(f"Failed to delete BA application segment {args.segment_id}: {err}")
    return OperationResult(
        success=True, message=f"BA application segment {args.segment_id} deleted successfully."
    ).model_dump()
