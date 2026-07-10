"""ZPA browser-access (BA) application segments — list, get, create, update, delete.

Mirrors v1's ``client.zpa.app_segments_ba_v2`` calls (``*_segment_ba``). A BA
segment is an application segment with browser-access (clientless) configuration;
the curated views reuse the standard app-segment shape plus the BA app config
member count.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, coalesce, pick, shape_many

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListBaSegmentsInput(BaseModel):
    """Inputs for listing ZPA browser-access application segments."""

    search: Annotated[
        Optional[str], Field(default=None, description="Server-side name substring match.")
    ] = None
    detail: Annotated[
        str, Field(default="summary", pattern="^(summary|full)$", description="Verbosity.")
    ] = "summary"
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
    detail: Annotated[
        str, Field(default="full", pattern="^(summary|full)$", description="Verbosity.")
    ] = "full"
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


class BaSegmentSummary(AgentView):
    """Lean view of a ZPA browser-access application segment."""

    id: str = Field(description="BA segment ID.")
    name: str = Field(description="Display name.")
    enabled: bool = Field(description="Whether enabled.")
    description: Optional[str] = Field(default=None, description="Admin description.")
    domain_name_count: int = Field(description="Number of domain names.")
    segment_group_id: Optional[str] = Field(default=None, description="Owning segment group ID.")
    clientless_app_count: int = Field(description="Number of browser-access app configs.")


class BaSegmentDetail(BaSegmentSummary):
    """Full view — adds members, ports, and clientless app names."""

    domain_names: list[str] = Field(default_factory=list, description="Domain names / FQDNs.")
    server_group_ids: list[str] = Field(default_factory=list, description="Server group IDs.")
    tcp_port_ranges: list[str] = Field(default_factory=list, description="TCP port ranges (flat).")
    udp_port_ranges: list[str] = Field(default_factory=list, description="UDP port ranges (flat).")
    clientless_app_names: list[str] = Field(
        default_factory=list, description="Browser-access app names."
    )
    microtenant_id: Optional[str] = Field(default=None, description="Owning microtenant, if any.")


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


# =============================================================================
# SHAPERS
# =============================================================================


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _domains(raw: dict[str, Any]) -> list[Any]:
    return coalesce(raw, "domain_names", "domainNames")


def _clientless(raw: dict[str, Any]) -> list[Any]:
    return coalesce(
        raw, "clientless_apps", "clientlessApps", "clientless_app_ids", "clientlessAppIds"
    )


def _server_groups(raw: dict[str, Any]) -> list[Any]:
    sgs = coalesce(raw, "server_groups", "serverGroups")
    return sgs or coalesce(raw, "server_group_ids", "serverGroupIds")


def shape_summary(raw: dict[str, Any]) -> BaSegmentSummary:
    return BaSegmentSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        enabled=bool(pick(raw, "enabled", default=False)),
        description=pick(raw, "description"),
        domain_name_count=len(_domains(raw)),
        segment_group_id=_opt_str(pick(raw, "segment_group_id", "segmentGroupId")),
        clientless_app_count=len(_clientless(raw)),
    )


def shape_detail(raw: dict[str, Any]) -> BaSegmentDetail:
    sgs = _server_groups(raw)
    clientless = _clientless(raw)
    return BaSegmentDetail(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        enabled=bool(pick(raw, "enabled", default=False)),
        description=pick(raw, "description"),
        domain_name_count=len(_domains(raw)),
        segment_group_id=_opt_str(pick(raw, "segment_group_id", "segmentGroupId")),
        clientless_app_count=len(clientless),
        domain_names=[str(d) for d in _domains(raw)],
        server_group_ids=[str(s.get("id", s)) if isinstance(s, dict) else str(s) for s in sgs],
        tcp_port_ranges=[str(p) for p in coalesce(raw, "tcp_port_ranges", "tcpPortRanges")],
        udp_port_ranges=[str(p) for p in coalesce(raw, "udp_port_ranges", "udpPortRanges")],
        clientless_app_names=[
            str(c.get("name", "")) for c in clientless if isinstance(c, dict) and c.get("name")
        ],
        microtenant_id=_opt_str(pick(raw, "microtenant_id", "microtenantId")),
    )


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
    output_view=BaSegmentSummary,
    is_list=True,
)
def zpa_list_application_segments_ba(args: ListBaSegmentsInput) -> list[dict[str, Any]]:
    """List ZPA browser-access (clientless) application segments as curated views."""
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
    shaper = shape_detail if args.detail == "full" else shape_summary
    return shape_many([s.as_dict() for s in (segments or [])], shaper)


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=GetBaSegmentInput,
    output_view=BaSegmentDetail,
    is_list=False,
)
def zpa_get_application_segment_ba(args: GetBaSegmentInput) -> dict[str, Any]:
    """Get one ZPA browser-access application segment as a curated view."""
    if not args.segment_id:
        raise ValueError("segment_id is required")
    client = get_zscaler_client(service="zpa")
    api = client.zpa.app_segments_ba_v2
    segment, _, err = api.get_segment_ba(
        args.segment_id, query_params={"microtenant_id": args.microtenant_id}
    )
    if err:
        raise RuntimeError(f"Failed to get BA application segment {args.segment_id}: {err}")
    shaper = shape_detail if args.detail == "full" else shape_summary
    return shaper(segment.as_dict()).model_dump()


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=CreateBaSegmentInput,
    output_view=BaSegmentDetail,
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
    return shape_detail(created.as_dict()).model_dump()


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=UpdateBaSegmentInput,
    output_view=BaSegmentDetail,
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
    return shape_detail(updated.as_dict()).model_dump()


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
