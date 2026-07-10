"""ZPA privileged-remote-access (PRA) application segments — CRUD.

Mirrors v1's ``client.zpa.app_segments_pra`` calls (``*_segment_pra``). A PRA
segment is an application segment carrying privileged-remote-access app configs
(RDP/SSH/VNC). The curated views surface the standard segment shape plus the PRA
app config count.
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


class ListPraSegmentsInput(BaseModel):
    """Inputs for listing ZPA PRA application segments."""

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


class GetPraSegmentInput(BaseModel):
    """Inputs for getting one ZPA PRA application segment."""

    segment_id: Annotated[str, Field(description="PRA segment ID (string).")]
    detail: Annotated[
        str, Field(default="full", pattern="^(summary|full)$", description="Verbosity.")
    ] = "full"
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


class PraSegmentSummary(AgentView):
    """Lean view of a ZPA PRA application segment."""

    id: str = Field(description="PRA segment ID.")
    name: str = Field(description="Display name.")
    enabled: bool = Field(description="Whether enabled.")
    description: Optional[str] = Field(default=None, description="Admin description.")
    domain_name_count: int = Field(description="Number of domain names.")
    segment_group_id: Optional[str] = Field(default=None, description="Owning segment group ID.")
    pra_app_count: int = Field(description="Number of privileged-access app configs.")


class PraSegmentDetail(PraSegmentSummary):
    """Full view — adds members, ports, and PRA app names."""

    domain_names: list[str] = Field(default_factory=list, description="Domain names / FQDNs.")
    server_group_ids: list[str] = Field(default_factory=list, description="Server group IDs.")
    tcp_port_ranges: list[str] = Field(default_factory=list, description="TCP port ranges (flat).")
    udp_port_ranges: list[str] = Field(default_factory=list, description="UDP port ranges (flat).")
    pra_app_names: list[str] = Field(
        default_factory=list, description="Privileged-access app names."
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


def _pra_apps(raw: dict[str, Any]) -> list[Any]:
    return coalesce(raw, "pra_apps", "praApps", "sra_apps", "sraApps")


def _server_groups(raw: dict[str, Any]) -> list[Any]:
    sgs = coalesce(raw, "server_groups", "serverGroups")
    return sgs or coalesce(raw, "server_group_ids", "serverGroupIds")


def shape_summary(raw: dict[str, Any]) -> PraSegmentSummary:
    return PraSegmentSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        enabled=bool(pick(raw, "enabled", default=False)),
        description=pick(raw, "description"),
        domain_name_count=len(_domains(raw)),
        segment_group_id=_opt_str(pick(raw, "segment_group_id", "segmentGroupId")),
        pra_app_count=len(_pra_apps(raw)),
    )


def shape_detail(raw: dict[str, Any]) -> PraSegmentDetail:
    sgs = _server_groups(raw)
    pra = _pra_apps(raw)
    return PraSegmentDetail(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        enabled=bool(pick(raw, "enabled", default=False)),
        description=pick(raw, "description"),
        domain_name_count=len(_domains(raw)),
        segment_group_id=_opt_str(pick(raw, "segment_group_id", "segmentGroupId")),
        pra_app_count=len(pra),
        domain_names=[str(d) for d in _domains(raw)],
        server_group_ids=[str(s.get("id", s)) if isinstance(s, dict) else str(s) for s in sgs],
        tcp_port_ranges=[str(p) for p in coalesce(raw, "tcp_port_ranges", "tcpPortRanges")],
        udp_port_ranges=[str(p) for p in coalesce(raw, "udp_port_ranges", "udpPortRanges")],
        pra_app_names=[
            str(c.get("name", "")) for c in pra if isinstance(c, dict) and c.get("name")
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
    output_view=PraSegmentSummary,
    is_list=True,
)
def zpa_list_application_segments_pra(args: ListPraSegmentsInput) -> list[dict[str, Any]]:
    """List ZPA privileged-remote-access application segments as curated views."""
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
    shaper = shape_detail if args.detail == "full" else shape_summary
    return shape_many([s.as_dict() for s in (segments or [])], shaper)


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=GetPraSegmentInput,
    output_view=PraSegmentDetail,
    is_list=False,
)
def zpa_get_application_segment_pra(args: GetPraSegmentInput) -> dict[str, Any]:
    """Get one ZPA privileged-remote-access application segment as a curated view."""
    if not args.segment_id:
        raise ValueError("segment_id is required")
    client = get_zscaler_client(service="zpa")
    api = client.zpa.app_segments_pra
    segment, _, err = api.get_segment_pra(
        args.segment_id, query_params={"microtenant_id": args.microtenant_id}
    )
    if err:
        raise RuntimeError(f"Failed to get PRA application segment {args.segment_id}: {err}")
    shaper = shape_detail if args.detail == "full" else shape_summary
    return shaper(segment.as_dict()).model_dump()


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=CreatePraSegmentInput,
    output_view=PraSegmentDetail,
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
    return shape_detail(created.as_dict()).model_dump()


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=UpdatePraSegmentInput,
    output_view=PraSegmentDetail,
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
    return shape_detail(updated.as_dict()).model_dump()


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=DeletePraSegmentInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_application_segment_pra(args: DeletePraSegmentInput) -> dict[str, Any]:
    """Delete a ZPA privileged-remote-access application segment (destructive write)."""
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
