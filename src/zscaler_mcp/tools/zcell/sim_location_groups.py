"""ZCell Sim Location Groups — agent-first v2 read tools.

Read-only surface over ``client.zcell.sim_location_groups``:

    * zcell_list_sim_location_groups — one curated row per SIM location group
    * zcell_get_sim_location_group    — the full geo-fence + linked-policy detail

The detail response nests geo-fence data and linked policies, so it is forced to
JSON and returns a single object.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many
from zscaler_mcp.tools.zcell._common import as_dict, as_dicts

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListSimLocationGroupsInput(BaseModel):
    """Inputs for listing SIM location groups."""

    name: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                "Server-side substring match on the group `name`. An empty "
                "result means no group name contains this string — do not retry "
                "with split keywords."
            ),
        ),
    ] = None
    page: Annotated[
        Optional[int], Field(default=None, ge=0, description="Page number (0-based).")
    ] = None
    size: Annotated[
        Optional[int], Field(default=None, ge=1, le=100, description="Page size (1-100).")
    ] = None


class GetSimLocationGroupInput(BaseModel):
    """Inputs for getting one SIM location group."""

    group_id: Annotated[str, Field(description="SIM location group ID (string, even if numeric).")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class SimLocationGroupSummary(AgentView):
    """Lean view — what an agent needs to LIST and REFERENCE a SIM location group."""

    id: Optional[str] = Field(
        default=None, description="Group ID. Use with zcell_get_sim_location_group."
    )
    name: Optional[str] = Field(default=None, description="Group display name.")
    tracked_devices: list[str] = Field(
        default_factory=list, description="ICCIDs of the SIMs tracked by this group (relational)."
    )


class SimLocationGroupDetail(AgentView):
    """Full view — geo-fence data, linked policies, and the ICCID membership buckets."""

    id: Optional[str] = Field(default=None, description="Group ID.")
    name: Optional[str] = Field(default=None, description="Group display name.")
    geo_fence_data: Optional[Any] = Field(
        default=None, description="Geo-fence definition (center, radius, zones)."
    )
    linked_policies: list[Any] = Field(
        default_factory=list, description="Anomaly policies linked to this group."
    )
    inside_and_tracked_iccids: list[str] = Field(
        default_factory=list, description="Tracked ICCIDs currently inside the fence."
    )
    inside_and_untracked_iccids: list[str] = Field(
        default_factory=list, description="Untracked ICCIDs currently inside the fence."
    )
    outside_and_tracked_iccids: list[str] = Field(
        default_factory=list, description="Tracked ICCIDs currently outside the fence."
    )


# =============================================================================
# SHAPERS
# =============================================================================


def _shape_summary(raw: dict[str, Any]) -> SimLocationGroupSummary:
    return SimLocationGroupSummary(
        id=_opt_str(pick(raw, "id")),
        name=pick(raw, "name"),
        tracked_devices=pick(raw, "tracked_devices", "trackedDevices", default=[]) or [],
    )


def _shape_detail(raw: dict[str, Any]) -> SimLocationGroupDetail:
    return SimLocationGroupDetail(
        id=_opt_str(pick(raw, "id")),
        name=pick(raw, "name"),
        geo_fence_data=pick(raw, "geo_fence_data", "geoFenceData"),
        linked_policies=pick(raw, "linked_policies", "linkedPolicies", default=[]) or [],
        inside_and_tracked_iccids=pick(
            raw, "inside_and_tracked_iccids", "insideAndTrackedIccids", default=[]
        )
        or [],
        inside_and_untracked_iccids=pick(
            raw, "inside_and_untracked_iccids", "insideAndUntrackedIccids", default=[]
        )
        or [],
        outside_and_tracked_iccids=pick(
            raw, "outside_and_tracked_iccids", "outsideAndTrackedIccids", default=[]
        )
        or [],
    )


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _query(*pairs: tuple[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in pairs if value is not None}


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_sim_location_groups",
    input_model=ListSimLocationGroupsInput,
    output_view=SimLocationGroupSummary,
    is_list=True,
)
def zcell_list_sim_location_groups(args: ListSimLocationGroupsInput) -> list[dict[str, Any]]:
    """List Zscaler Cellular SIM location groups as curated, agent-facing views.

    Read-only. Returns one row per group (id, name, tracked ICCIDs). Use the
    returned `id` with `zcell_get_sim_location_group` for the geo-fence and
    linked-policy detail.
    """
    client = get_zscaler_client(service="zcell")

    groups, _, err = client.zcell.sim_location_groups.list_sim_location_groups(
        query_params=_query(("name", args.name), ("page", args.page), ("size", args.size))
    )
    if err:
        raise RuntimeError(f"Failed to list SIM location groups: {err}")
    return shape_many(as_dicts(groups), _shape_summary)


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_sim_location_groups",
    input_model=GetSimLocationGroupInput,
    output_view=SimLocationGroupDetail,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zcell_get_sim_location_group(args: GetSimLocationGroupInput) -> dict[str, Any]:
    """Get one Zscaler Cellular SIM location group as a curated, agent-facing view.

    Read-only. Adds the geo-fence definition, linked anomaly policies, and the
    inside/outside ICCID membership buckets on top of the summary fields.
    """
    if not args.group_id:
        raise ValueError("group_id is required")

    client = get_zscaler_client(service="zcell")

    group, _, err = client.zcell.sim_location_groups.get_sim_location_group(group_id=args.group_id)
    if err:
        raise RuntimeError(f"Failed to get SIM location group {args.group_id}: {err}")
    return _shape_detail(as_dict(group)).model_dump()
