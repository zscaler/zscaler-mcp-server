"""ZPA privileged-remote-access (PRA) application segments — CRUD.

Mirrors v1's ``client.zpa.app_segments_pra`` calls (``*_segment_pra``). A PRA
segment is an application segment carrying privileged-remote-access app configs
(RDP/SSH/VNC). The full records surface the standard segment shape plus the PRA
app config count.
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


class ListPraSegmentsInput(BaseModel):
    """Inputs for listing ZPA PRA application segments."""

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


class GetPraSegmentInput(BaseModel):
    """Inputs for getting one ZPA PRA application segment."""

    segment_id: Annotated[str, Field(description="PRA segment ID (string).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant scoping.")
    ] = None


class CreatePraSegmentInput(BaseModel):
    """Inputs for creating a ZPA PRA application segment."""

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
    common_apps_dto: Annotated[
        Optional[dict[str, Any]],
        Field(default=None, description="PRA app configs (RDP/SSH/VNC) forwarded as-is."),
    ] = None
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    enabled: Annotated[bool, Field(default=True, description="Whether enabled.")] = True
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant scoping.")
    ] = None
    advanced: Annotated[
        Optional[dict[str, Any]], Field(default=None, description="Advanced SDK fields.")
    ] = None


class UpdatePraSegmentInput(BaseModel):
    """Inputs for updating a ZPA PRA application segment (partial)."""

    segment_id: Annotated[str, Field(description="PRA segment ID (string).")]
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
    common_apps_dto: Annotated[
        Optional[dict[str, Any]], Field(default=None, description="New PRA app configs.")
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


class DeletePraSegmentInput(BaseModel):
    """Inputs for deleting a ZPA PRA application segment (destructive)."""

    segment_id: Annotated[str, Field(description="PRA segment ID (string).")]
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
        "common_apps_dto",
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
    input_model=ListPraSegmentsInput,
    is_list=True,
)
def zpa_list_application_segments_pra(args: ListPraSegmentsInput) -> list[dict[str, Any]]:
    """List ZPA privileged-remote-access application segments."""
    client = get_zscaler_client(service="zpa")
    api = client.zpa.app_segments_pra
    qp: dict[str, Any] = {"microtenant_id": args.microtenant_id}
    if args.search:
        qp["search"] = args.search
    if args.page is not None:
        qp["page"] = str(args.page)
    if args.page_size is not None:
        qp["page_size"] = str(args.page_size)
    segments, _, err = api.list_segments_pra(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list PRA application segments: {err}")
    return shape_many([s.as_dict() for s in (segments or [])])


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=GetPraSegmentInput,
    is_list=False,
)
def zpa_get_application_segment_pra(args: GetPraSegmentInput) -> dict[str, Any]:
    """Get one ZPA privileged-remote-access application segment."""
    if not args.segment_id:
        raise ValueError("segment_id is required")
    client = get_zscaler_client(service="zpa")
    api = client.zpa.app_segments_pra
    segment, _, err = api.get_segment_pra(
        args.segment_id, query_params={"microtenant_id": args.microtenant_id}
    )
    if err:
        raise RuntimeError(f"Failed to get PRA application segment {args.segment_id}: {err}")
    return shape_one(segment.as_dict())


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=CreatePraSegmentInput,
    is_list=False,
)
def zpa_create_application_segment_pra(args: CreatePraSegmentInput) -> dict[str, Any]:
    """Create a ZPA privileged-remote-access application segment (write)."""
    if not args.name or not args.segment_group_id:
        raise ValueError("name and segment_group_id are required")
    client = get_zscaler_client(service="zpa")
    api = client.zpa.app_segments_pra
    created, _, err = api.add_segment_pra(**_build_body(args))
    if err:
        raise RuntimeError(f"Failed to create PRA application segment: {err}")
    return shape_one(created.as_dict())


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=UpdatePraSegmentInput,
    is_list=False,
)
def zpa_update_application_segment_pra(args: UpdatePraSegmentInput) -> dict[str, Any]:
    """Update a ZPA privileged-remote-access application segment (write). Only provided fields are sent."""
    if not args.segment_id:
        raise ValueError("segment_id is required for update")
    client = get_zscaler_client(service="zpa")
    api = client.zpa.app_segments_pra
    updated, _, err = api.update_segment_pra(args.segment_id, **_build_body(args))
    if err:
        raise RuntimeError(f"Failed to update PRA application segment {args.segment_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=DeletePraSegmentInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_application_segment_pra(args: DeletePraSegmentInput) -> dict[str, Any]:
    """Delete a ZPA privileged-remote-access application segment (destructive write).

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    if not args.segment_id:
        raise ValueError("segment_id is required for delete")
    client = get_zscaler_client(service="zpa")
    api = client.zpa.app_segments_pra
    _, _, err = api.delete_segment_pra(args.segment_id, microtenant_id=args.microtenant_id)
    if err:
        raise RuntimeError(f"Failed to delete PRA application segment {args.segment_id}: {err}")
    return OperationResult(
        success=True, message=f"PRA application segment {args.segment_id} deleted successfully."
    ).model_dump()
