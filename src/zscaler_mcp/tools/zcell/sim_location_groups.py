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
from zscaler_mcp.shaping import shape_many, shape_one
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
    is_list=True,
)
def zcell_list_sim_location_groups(args: ListSimLocationGroupsInput) -> list[dict[str, Any]]:
    """List Zscaler Cellular SIM location groups.

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
    return shape_many(as_dicts(groups))


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_sim_location_groups",
    input_model=GetSimLocationGroupInput,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zcell_get_sim_location_group(args: GetSimLocationGroupInput) -> dict[str, Any]:
    """Get one Zscaler Cellular SIM location group.

    Read-only. Adds the geo-fence definition, linked anomaly policies, and the
    inside/outside ICCID membership buckets on top of the summary fields.
    """
    if not args.group_id:
        raise ValueError("group_id is required")

    client = get_zscaler_client(service="zcell")

    group, _, err = client.zcell.sim_location_groups.get_sim_location_group(group_id=args.group_id)
    if err:
        raise RuntimeError(f"Failed to get SIM location group {args.group_id}: {err}")
    return shape_one(as_dict(group))
