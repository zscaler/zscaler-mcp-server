"""ZPA application segments (standard) — list, get, create, update, delete.

Mirrors v1's ``client.zpa.application_segment`` calls. The v1 create/update tools
expose ~30 optional knobs; v2 keeps the decision-bearing ones as typed fields and
funnels the long tail of advanced toggles through a single ``advanced`` dict so
the input schema stays readable without losing any capability (every v1 field is
still settable). Output is curated to a lean summary / fuller detail.
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


class ListAppSegmentsInput(BaseModel):
    """Inputs for listing ZPA application segments."""

    search: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                "Server-side substring match on the segment `name`. An empty result "
                "means no segment name contains this string — do not retry broadened."
            ),
        ),
    ] = None
    detail: Annotated[
        str,
        Field(default="summary", pattern="^(summary|full)$", description="Response verbosity."),
    ] = "summary"
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant scoping.")
    ] = None
    page: Annotated[Optional[int], Field(default=None, ge=1, description="Page number.")] = None
    page_size: Annotated[
        Optional[int], Field(default=None, ge=1, le=500, description="Per page.")
    ] = None


class GetAppSegmentInput(BaseModel):
    """Inputs for getting one ZPA application segment."""

    segment_id: Annotated[str, Field(description="Segment ID (string, even if numeric).")]
    detail: Annotated[
        str, Field(default="full", pattern="^(summary|full)$", description="Response verbosity.")
    ] = "full"
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant scoping.")
    ] = None


class CreateAppSegmentInput(BaseModel):
    """Inputs for creating a ZPA application segment.

    Common fields are typed; less-common toggles (double_encrypt, icmp_access_type,
    bypass_type, health_*, match_style, inspect_traffic_with_zia, …) go in
    ``advanced`` and are forwarded to the SDK unchanged.
    """

    name: Annotated[str, Field(description="Segment name.")]
    segment_group_id: Annotated[str, Field(description="Owning segment group ID.")]
    domain_names: Annotated[
        Optional[list[str]], Field(default=None, description="Domain names / FQDNs served.")
    ] = None
    server_group_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Server group IDs to attach.")
    ] = None
    tcp_port_ranges: Annotated[
        Optional[list[str]],
        Field(default=None, description="Flat TCP port list, e.g. ['443','443','8080','8080']."),
    ] = None
    udp_port_ranges: Annotated[
        Optional[list[str]], Field(default=None, description="Flat UDP port list.")
    ] = None
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    enabled: Annotated[bool, Field(default=True, description="Whether the segment is enabled.")] = (
        True
    )
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant scoping.")
    ] = None
    advanced: Annotated[
        Optional[dict[str, Any]],
        Field(
            default=None,
            description=(
                "Advanced SDK fields forwarded as-is (e.g. bypass_type, "
                "icmp_access_type, double_encrypt, health_check_type, "
                "inspect_traffic_with_zia, match_style, tcp_port_range structured)."
            ),
        ),
    ] = None


class UpdateAppSegmentInput(BaseModel):
    """Inputs for updating a ZPA application segment (partial)."""

    segment_id: Annotated[str, Field(description="Segment ID (string, even if numeric).")]
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
    description: Annotated[Optional[str], Field(default=None, description="New description.")] = (
        None
    )
    enabled: Annotated[Optional[bool], Field(default=None, description="Enable/disable.")] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant scoping.")
    ] = None
    advanced: Annotated[
        Optional[dict[str, Any]],
        Field(default=None, description="Advanced SDK fields forwarded as-is (see create)."),
    ] = None


class DeleteAppSegmentInput(BaseModel):
    """Inputs for deleting a ZPA application segment (destructive)."""

    segment_id: Annotated[str, Field(description="Segment ID (string, even if numeric).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant scoping.")
    ] = None


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class AppSegmentSummary(AgentView):
    """Lean view of a ZPA application segment."""

    id: str = Field(description="Segment ID. Use this in follow-up calls.")
    name: str = Field(description="Display name.")
    enabled: bool = Field(description="Whether the segment is enabled.")
    description: Optional[str] = Field(default=None, description="Admin description.")
    domain_name_count: int = Field(description="Number of domain names served.")
    segment_group_id: Optional[str] = Field(default=None, description="Owning segment group ID.")
    server_group_count: int = Field(description="Number of attached server groups.")


class AppSegmentDetail(AppSegmentSummary):
    """Full view — adds members, ports, and key behavior toggles."""

    domain_names: list[str] = Field(default_factory=list, description="Domain names / FQDNs.")
    server_group_ids: list[str] = Field(
        default_factory=list, description="Attached server group IDs."
    )
    tcp_port_ranges: list[str] = Field(default_factory=list, description="TCP port ranges (flat).")
    udp_port_ranges: list[str] = Field(default_factory=list, description="UDP port ranges (flat).")
    bypass_type: Optional[str] = Field(default=None, description="Bypass type.")
    health_check_type: Optional[str] = Field(default=None, description="Health check type.")
    icmp_access_type: Optional[str] = Field(default=None, description="ICMP access behavior.")
    double_encrypt: Optional[bool] = Field(default=None, description="Double encryption enabled.")
    inspect_traffic_with_zia: Optional[bool] = Field(
        default=None, description="Source IP Anchoring (forward to ZIA)."
    )
    microtenant_id: Optional[str] = Field(default=None, description="Owning microtenant, if any.")


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


# =============================================================================
# SHAPERS
# =============================================================================


def _domains(raw: dict[str, Any]) -> list[Any]:
    return coalesce(raw, "domain_names", "domainNames")


def _server_groups(raw: dict[str, Any]) -> list[Any]:
    sgs = coalesce(raw, "server_groups", "serverGroups")
    if sgs:
        return sgs
    return coalesce(raw, "server_group_ids", "serverGroupIds")


def _ports(raw: dict[str, Any], *keys: str) -> list[str]:
    return [str(p) for p in coalesce(raw, *keys)]


def shape_summary(raw: dict[str, Any]) -> AppSegmentSummary:
    return AppSegmentSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        enabled=bool(pick(raw, "enabled", default=False)),
        description=pick(raw, "description"),
        domain_name_count=len(_domains(raw)),
        segment_group_id=_opt_str(pick(raw, "segment_group_id", "segmentGroupId")),
        server_group_count=len(_server_groups(raw)),
    )


def shape_detail(raw: dict[str, Any]) -> AppSegmentDetail:
    sgs = _server_groups(raw)
    return AppSegmentDetail(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        enabled=bool(pick(raw, "enabled", default=False)),
        description=pick(raw, "description"),
        domain_name_count=len(_domains(raw)),
        segment_group_id=_opt_str(pick(raw, "segment_group_id", "segmentGroupId")),
        server_group_count=len(sgs),
        domain_names=[str(d) for d in _domains(raw)],
        server_group_ids=[str(s.get("id", s)) if isinstance(s, dict) else str(s) for s in sgs],
        tcp_port_ranges=_ports(raw, "tcp_port_ranges", "tcpPortRanges"),
        udp_port_ranges=_ports(raw, "udp_port_ranges", "udpPortRanges"),
        bypass_type=pick(raw, "bypass_type", "bypassType"),
        health_check_type=pick(raw, "health_check_type", "healthCheckType"),
        icmp_access_type=pick(raw, "icmp_access_type", "icmpAccessType"),
        double_encrypt=pick(raw, "double_encrypt", "doubleEncrypt"),
        inspect_traffic_with_zia=pick(raw, "inspect_traffic_with_zia", "inspectTrafficWithZia"),
        microtenant_id=_opt_str(pick(raw, "microtenant_id", "microtenantId")),
    )


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _build_body(args: Any, *, include_required: bool) -> dict[str, Any]:
    """Build the SDK kwargs body from a create/update input model."""
    body: dict[str, Any] = {}
    simple = [
        "name",
        "description",
        "enabled",
        "domain_names",
        "segment_group_id",
        "server_group_ids",
        "tcp_port_ranges",
        "udp_port_ranges",
    ]
    for field in simple:
        val = getattr(args, field, None)
        if val is not None:
            body[field] = val
    if getattr(args, "microtenant_id", None):
        body["microtenant_id"] = args.microtenant_id
    advanced = getattr(args, "advanced", None)
    if advanced:
        body.update(advanced)
    return body


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=ListAppSegmentsInput,
    output_view=AppSegmentSummary,
    is_list=True,
)
def zpa_list_application_segments(args: ListAppSegmentsInput) -> list[dict[str, Any]]:
    """List ZPA application segments as curated, agent-facing views.

    Lean summaries by default; pass `detail='full'` for members/ports/toggles.
    """
    client = get_zscaler_client(service="zpa")
    api = client.zpa.application_segment

    qp: dict[str, Any] = {"microtenant_id": args.microtenant_id}
    if args.search:
        qp["search"] = args.search
    if args.page is not None:
        qp["page"] = str(args.page)
    if args.page_size is not None:
        qp["page_size"] = str(args.page_size)

    segments, _, err = api.list_segments(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list application segments: {err}")

    shaper = shape_detail if args.detail == "full" else shape_summary
    return shape_many([s.as_dict() for s in (segments or [])], shaper)


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=GetAppSegmentInput,
    output_view=AppSegmentDetail,
    is_list=False,
)
def zpa_get_application_segment(args: GetAppSegmentInput) -> dict[str, Any]:
    """Get one ZPA application segment as a curated view."""
    if not args.segment_id:
        raise ValueError("segment_id is required")
    client = get_zscaler_client(service="zpa")
    api = client.zpa.application_segment
    segment, _, err = api.get_segment(
        args.segment_id, query_params={"microtenant_id": args.microtenant_id}
    )
    if err:
        raise RuntimeError(f"Failed to get application segment {args.segment_id}: {err}")
    shaper = shape_detail if args.detail == "full" else shape_summary
    return shaper(segment.as_dict()).model_dump()


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=CreateAppSegmentInput,
    output_view=AppSegmentDetail,
    is_list=False,
)
def zpa_create_application_segment(args: CreateAppSegmentInput) -> dict[str, Any]:
    """Create a ZPA application segment (write).

    Requires `name` + `segment_group_id` and at least one port range (TCP or UDP,
    via `tcp_port_ranges`/`udp_port_ranges` or `advanced`). Gated by HMAC
    confirmation + `--write-tools`.
    """
    if not args.name or not args.segment_group_id:
        raise ValueError("name and segment_group_id are required")
    has_ports = (
        args.tcp_port_ranges
        or args.udp_port_ranges
        or (args.advanced and any(k.startswith(("tcp_port", "udp_port")) for k in args.advanced))
    )
    if not has_ports:
        raise ValueError("At least one port range is required (tcp_port_ranges/udp_port_ranges).")

    client = get_zscaler_client(service="zpa")
    api = client.zpa.application_segment
    created, _, err = api.add_segment(**_build_body(args, include_required=True))
    if err:
        raise RuntimeError(f"Failed to create application segment: {err}")
    return shape_detail(created.as_dict()).model_dump()


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=UpdateAppSegmentInput,
    output_view=AppSegmentDetail,
    is_list=False,
)
def zpa_update_application_segment(args: UpdateAppSegmentInput) -> dict[str, Any]:
    """Update a ZPA application segment (write). Only provided fields are sent."""
    if not args.segment_id:
        raise ValueError("segment_id is required for update")
    client = get_zscaler_client(service="zpa")
    api = client.zpa.application_segment
    updated, _, err = api.update_segment(
        args.segment_id, **_build_body(args, include_required=False)
    )
    if err:
        raise RuntimeError(f"Failed to update application segment {args.segment_id}: {err}")
    return shape_detail(updated.as_dict()).model_dump()


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_app_segments",
    input_model=DeleteAppSegmentInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_application_segment(args: DeleteAppSegmentInput) -> dict[str, Any]:
    """Delete a ZPA application segment (destructive write). Cannot be undone."""
    if not args.segment_id:
        raise ValueError("segment_id is required for delete")
    client = get_zscaler_client(service="zpa")
    api = client.zpa.application_segment
    _, _, err = api.delete_segment(args.segment_id, microtenant_id=args.microtenant_id)
    if err:
        raise RuntimeError(f"Failed to delete application segment {args.segment_id}: {err}")
    return OperationResult(
        success=True, message=f"Application segment {args.segment_id} deleted successfully."
    ).model_dump()
