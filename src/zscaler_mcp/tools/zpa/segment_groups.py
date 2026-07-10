"""ZPA segment groups — reference v2 ("second step") tool family.

This is the canonical example of the agent-first pattern described in DESIGN.md.
Compare it to v1's ``zscaler_mcp/tools/zpa/segment_groups.py``:

    v1:  fetch ──► result.as_dict() ──► agent          (the full SDK object)
    v2:  fetch ──► raw SDK model ──► SHAPER ──► curated, schema-backed view

A v2 tool has these parts (vs v1's two — fetch + ``as_dict()``):

    1. Input model   — typed, validated (Pydantic)
    2. Output view   — Pydantic model declaring the curated agent-facing shape
    3. Shaper        — deterministic SDK-dict -> view mapping (the design work)
    4. SDK call      — UNCHANGED: client.zpa.segment_groups.list_groups(...)
    5. @tool         — declares the tool (action/schemas/toolset) AT the
                       definition site and self-registers at import time; no
                       separate catalog entry (DESIGN.md §6).

The SDK still does the API call. The new things are the shaper, the declared
output schema, and the self-registration.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, coalesce, pick, shape_many

# =============================================================================
# 1. INPUT MODELS  (typed + validated; the inputSchema source of truth)
# =============================================================================


class ListSegmentGroupsInput(BaseModel):
    """Inputs for listing ZPA segment groups."""

    search: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                "Server-side substring match on the segment group's `name`. "
                "An empty result means no group name contains this string — "
                "do not retry with split keywords or no filter."
            ),
        ),
    ] = None
    detail: Annotated[
        str,
        Field(
            default="summary",
            pattern="^(summary|full)$",
            description=(
                "Response verbosity. 'summary' (default) returns the lean, "
                "agent-purposed view. 'full' adds provenance/audit fields for "
                "the rare case you genuinely need them."
            ),
        ),
    ] = "summary"
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None
    page: Annotated[Optional[int], Field(default=None, ge=1, description="Page number.")] = None
    page_size: Annotated[
        Optional[int], Field(default=None, ge=1, le=500, description="Items per page.")
    ] = None


class GetSegmentGroupInput(BaseModel):
    """Inputs for getting one ZPA segment group."""

    group_id: Annotated[
        str, Field(description="ID of the segment group (string, even if numeric).")
    ]
    detail: Annotated[
        str,
        Field(default="full", pattern="^(summary|full)$", description="Response verbosity."),
    ] = "full"
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class CreateSegmentGroupInput(BaseModel):
    """Inputs for creating a ZPA segment group."""

    name: Annotated[str, Field(description="Display name for the new segment group.")]
    enabled: Annotated[
        bool, Field(default=True, description="Whether the group is enabled on creation.")
    ] = True
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class UpdateSegmentGroupInput(BaseModel):
    """Inputs for updating a ZPA segment group (partial)."""

    group_id: Annotated[
        str, Field(description="ID of the segment group (string, even if numeric).")
    ]
    name: Annotated[Optional[str], Field(default=None, description="New display name.")] = None
    description: Annotated[Optional[str], Field(default=None, description="New description.")] = (
        None
    )
    enabled: Annotated[Optional[bool], Field(default=None, description="Enable/disable.")] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class DeleteSegmentGroupInput(BaseModel):
    """Inputs for deleting a ZPA segment group (destructive)."""

    group_id: Annotated[
        str, Field(description="ID of the segment group (string, even if numeric).")
    ]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


# =============================================================================
# 3. OUTPUT VIEWS  (curated agent-facing shape; the outputSchema source of truth)
# =============================================================================


class SegmentGroupSummary(AgentView):
    """Lean view — what an agent needs to LIST and REFERENCE a segment group.

    Field policy (DESIGN.md §5 Pillar A): every field here is identifying, decision-
    bearing, relational, or explanatory. Provenance/transport fields from the
    SDK object (creationTime, modifiedBy, configSpace, href, ...) are dropped.
    """

    id: str = Field(description="Segment group ID. Use this in follow-up calls.")
    name: str = Field(description="Display name.")
    enabled: bool = Field(description="Whether the group is enabled (decision-bearing).")
    description: Optional[str] = Field(default=None, description="Admin description.")
    application_segment_count: int = Field(
        description="Number of application segments in this group (relational signal)."
    )


class SegmentGroupDetail(SegmentGroupSummary):
    """Full view — summary plus the relational + provenance fields.

    Returned only when ``detail='full'``. Still curated (not the raw SDK dict):
    relational ids are surfaced explicitly, audit fields are named clearly.
    """

    application_segment_ids: list[str] = Field(
        default_factory=list, description="IDs of the application segments in this group."
    )
    microtenant_id: Optional[str] = Field(default=None, description="Owning microtenant, if any.")
    created_time: Optional[str] = Field(
        default=None, description="Creation timestamp (provenance)."
    )
    modified_time: Optional[str] = Field(
        default=None, description="Last-modified timestamp (provenance)."
    )


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


# =============================================================================
# 4. SHAPERS  (deterministic SDK-dict -> view; THE design work)
# =============================================================================


def _app_segments(raw: dict[str, Any]) -> list[dict[str, Any]]:
    return coalesce(raw, "applications", "app_segments", "applicationSegments")


def shape_summary(raw: dict[str, Any]) -> SegmentGroupSummary:
    """Map a raw SDK segment-group dict onto the lean summary view."""
    return SegmentGroupSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        enabled=bool(pick(raw, "enabled", default=False)),
        description=pick(raw, "description"),
        application_segment_count=len(_app_segments(raw)),
    )


def shape_detail(raw: dict[str, Any]) -> SegmentGroupDetail:
    """Map a raw SDK segment-group dict onto the full detail view."""
    segs = _app_segments(raw)
    return SegmentGroupDetail(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        enabled=bool(pick(raw, "enabled", default=False)),
        description=pick(raw, "description"),
        application_segment_count=len(segs),
        application_segment_ids=[str(pick(s, "id", default="")) for s in segs],
        microtenant_id=pick(raw, "microtenant_id", "microtenantId"),
        created_time=pick(raw, "creation_time", "creationTime"),
        modified_time=pick(raw, "modified_time", "modifiedTime"),
    )


# =============================================================================
# 2. TOOL FUNCTIONS  (input -> SDK call -> shaper -> curated output)
# =============================================================================


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_segment_groups",
    input_model=ListSegmentGroupsInput,
    output_view=SegmentGroupSummary,  # the default-detail shape
    is_list=True,
)
def zpa_list_segment_groups(args: ListSegmentGroupsInput) -> list[dict[str, Any]]:
    """List ZPA segment groups as curated, agent-facing views.

    Returns lean summaries by default (`detail='summary'`); pass `detail='full'`
    for the relational + provenance fields. The response shape is declared by
    the tool's outputSchema (SegmentGroupSummary / SegmentGroupDetail).
    """
    client = get_zscaler_client(service="zpa")
    sg = client.zpa.segment_groups

    qp: dict[str, Any] = {"microtenant_id": args.microtenant_id}
    if args.search:
        qp["search"] = args.search
    if args.page is not None:
        qp["page"] = str(args.page)
    if args.page_size is not None:
        qp["page_size"] = str(args.page_size)

    groups, _, err = sg.list_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list segment groups: {err}")

    raw_dicts = [g.as_dict() for g in (groups or [])]
    shaper = shape_detail if args.detail == "full" else shape_summary
    return shape_many(raw_dicts, shaper)


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_segment_groups",
    input_model=GetSegmentGroupInput,
    output_view=SegmentGroupDetail,
    is_list=False,
)
def zpa_get_segment_group(args: GetSegmentGroupInput) -> dict[str, Any]:
    """Get one ZPA segment group as a curated, agent-facing view."""
    if not args.group_id:
        raise ValueError("group_id is required")

    client = get_zscaler_client(service="zpa")
    sg = client.zpa.segment_groups

    result, _, err = sg.get_group(
        args.group_id, query_params={"microtenant_id": args.microtenant_id}
    )
    if err:
        raise RuntimeError(f"Failed to get segment group {args.group_id}: {err}")

    raw = result.as_dict()
    shaper = shape_detail if args.detail == "full" else shape_summary
    return shaper(raw).model_dump()


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_segment_groups",
    input_model=CreateSegmentGroupInput,
    output_view=SegmentGroupDetail,
    is_list=False,
)
def zpa_create_segment_group(args: CreateSegmentGroupInput) -> dict[str, Any]:
    """Create a ZPA segment group and return the curated detail view.

    Write tool: gated by the server's HMAC write-confirmation. The first call
    returns a confirmation prompt + token; the agent re-issues with the token
    (in `kwargs`) once the user approves. Write tools are also disabled unless
    the operator enables them via --write-tools.
    """
    if not args.name:
        raise ValueError("name is required")

    client = get_zscaler_client(service="zpa")
    sg = client.zpa.segment_groups

    payload: dict[str, Any] = {"name": args.name, "enabled": args.enabled}
    if args.description is not None:
        payload["description"] = args.description
    if args.microtenant_id is not None:
        payload["microtenant_id"] = args.microtenant_id

    result, _, err = sg.add_group(**payload)
    if err:
        raise RuntimeError(f"Failed to create segment group: {err}")

    return shape_detail(result.as_dict()).model_dump()


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_segment_groups",
    input_model=UpdateSegmentGroupInput,
    output_view=SegmentGroupDetail,
    is_list=False,
)
def zpa_update_segment_group(args: UpdateSegmentGroupInput) -> dict[str, Any]:
    """Update a ZPA segment group and return the curated detail view (write).

    Gated by HMAC write-confirmation and `--write-tools`. Only the provided
    fields are sent (uses the SDK's v2 update path).
    """
    if not args.group_id:
        raise ValueError("group_id is required for update")

    client = get_zscaler_client(service="zpa")
    sg = client.zpa.segment_groups

    body: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "enabled": args.enabled,
    }
    if args.microtenant_id:
        body["microtenant_id"] = args.microtenant_id

    result, _, err = sg.update_group_v2(args.group_id, **body)
    if err:
        raise RuntimeError(f"Failed to update segment group {args.group_id}: {err}")
    return shape_detail(result.as_dict()).model_dump()


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_segment_groups",
    input_model=DeleteSegmentGroupInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_segment_group(args: DeleteSegmentGroupInput) -> dict[str, Any]:
    """Delete a ZPA segment group (destructive write).

    Cannot be undone. Gated by HMAC write-confirmation and `--write-tools`.
    """
    if not args.group_id:
        raise ValueError("group_id is required for delete")

    client = get_zscaler_client(service="zpa")
    sg = client.zpa.segment_groups

    _, _, err = sg.delete_group(args.group_id, microtenant_id=args.microtenant_id)
    if err:
        raise RuntimeError(f"Failed to delete segment group {args.group_id}: {err}")
    return OperationResult(
        success=True, message=f"Segment group {args.group_id} deleted successfully."
    ).model_dump()


# NOTE: there is no manual tool list here. Each function above registers itself
# via the @tool decorator at import time (DESIGN.md §6). The server discovers
# tools by importing this package; adding a new tool means adding a decorated
# function, nothing else — there is no central catalog to keep in sync.
