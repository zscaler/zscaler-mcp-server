"""ZPA segment groups — the reference tool family. Copy this shape.

    fetch ──► record.as_dict() ──► agent        (the API's record, untouched)

A tool has three parts:

    1. Input model   — typed, validated (Pydantic). ENUMERATE every field here:
                       inputs are a closed set the caller cannot discover on its
                       own, which is why the Zscaler SDK documents every settable
                       attribute of ``add_segment`` while describing the response
                       as just ``record.as_dict()``.
    2. SDK call      — unchanged: ``client.zpa.segment_groups.list_groups(...)``.
    3. @tool         — declares action/schemas/toolset AT the definition site and
                       self-registers at import time; there is no central catalog
                       to keep in sync.

There is deliberately NO output view. A read returns the API record verbatim,
because a resource's attribute set belongs to the API: any list written here
would be a snapshot that goes stale the moment engineering ships a field, and
before issue #88 it doubled as a whitelist that deleted what it didn't
recognize. Response size is the CALLER's lever — every list tool accepts a
JMESPath ``query`` (wired centrally in ``registry/fastmcp_bridge``), so the
agent projects what it wants instead of the server guessing.

``OperationResult`` below is the one legitimate view: a delete acknowledgement
is a shape the server invents, not a record it fetched.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, shape_many, shape_one

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


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


# =============================================================================
# 4. SHAPERS  (deterministic SDK-dict -> view; THE design work)
# =============================================================================




# =============================================================================
# 2. TOOL FUNCTIONS  (input -> SDK call -> shaper -> curated output)
# =============================================================================


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_segment_groups",
    input_model=ListSegmentGroupsInput,
    is_list=True,
)
def zpa_list_segment_groups(args: ListSegmentGroupsInput) -> list[dict[str, Any]]:
    """List ZPA segment groups.

    Each row is the full segment-group record with normalized highlights
    (ids, enabled state, application-segment counts/ids, timestamps) on top.
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
    return shape_many(raw_dicts)


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_segment_groups",
    input_model=GetSegmentGroupInput,
    is_list=False,
)
def zpa_get_segment_group(args: GetSegmentGroupInput) -> dict[str, Any]:
    """Get one ZPA segment group."""
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
    return shape_one(raw)


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_segment_groups",
    input_model=CreateSegmentGroupInput,
    is_list=False,
)
def zpa_create_segment_group(args: CreateSegmentGroupInput) -> dict[str, Any]:
    """Create a ZPA segment group and return the full record.

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

    return shape_one(result.as_dict())


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_segment_groups",
    input_model=UpdateSegmentGroupInput,
    is_list=False,
)
def zpa_update_segment_group(args: UpdateSegmentGroupInput) -> dict[str, Any]:
    """Update a ZPA segment group and return the full record (write).

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
    return shape_one(result.as_dict())


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
