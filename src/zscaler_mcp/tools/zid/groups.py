"""ZIdentity (ZID) groups — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zid/groups.py`` but adds the v2 shaping layer:
the verbose SDK group / membership records are curated down to the identifying
+ relational subset an admin actually reasons about. See DESIGN.md §5.

v1 exposed a free-form ``query_params`` dict plus a JMESPath ``query`` knob; v2
declares typed inputs and a curated, schema-backed output view instead.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many, shape_one

# =============================================================================
# 1. INPUT MODELS  (typed + validated; the inputSchema source of truth)
# =============================================================================


class ListGroupsInput(BaseModel):
    """Inputs for listing ZIdentity groups."""

    name: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                "Case-insensitive partial match on the group's `name` "
                "(server-side `name[like]` filter). An empty result means no "
                "group name contains this string — do not retry with split "
                "keywords or no filter."
            ),
        ),
    ] = None
    exclude_dynamic_groups: Annotated[
        Optional[bool],
        Field(default=None, description="When true, omit dynamically-evaluated groups."),
    ] = None
    offset: Annotated[
        Optional[int], Field(default=None, ge=0, description="Pagination offset (records to skip).")
    ] = None
    limit: Annotated[
        Optional[int], Field(default=None, ge=1, le=1000, description="Max records to return.")
    ] = None


class GetGroupInput(BaseModel):
    """Inputs for getting one ZIdentity group."""

    group_id: Annotated[str, Field(description="ID of the group (string, even if numeric).")]


class SearchGroupsInput(BaseModel):
    """Inputs for searching ZIdentity groups by name."""

    name: Annotated[
        str,
        Field(description="Group name to search for (case-insensitive partial match)."),
    ]
    offset: Annotated[
        Optional[int], Field(default=None, ge=0, description="Pagination offset (records to skip).")
    ] = None
    limit: Annotated[
        Optional[int], Field(default=None, ge=1, le=1000, description="Max records to return.")
    ] = None


class GroupUsersInput(BaseModel):
    """Inputs for listing the users that belong to a ZIdentity group by ID."""

    group_id: Annotated[str, Field(description="ID of the group (string, even if numeric).")]
    offset: Annotated[
        Optional[int], Field(default=None, ge=0, description="Pagination offset (records to skip).")
    ] = None
    limit: Annotated[
        Optional[int], Field(default=None, ge=1, le=1000, description="Max records to return.")
    ] = None


class GroupUsersByNameInput(BaseModel):
    """Inputs for listing the users in a ZIdentity group resolved by group name."""

    name: Annotated[
        str,
        Field(
            description=(
                "Group name to resolve (case-insensitive partial match). The "
                "first matching group's members are returned."
            )
        ),
    ]
    offset: Annotated[
        Optional[int], Field(default=None, ge=0, description="Pagination offset (records to skip).")
    ] = None
    limit: Annotated[
        Optional[int], Field(default=None, ge=1, le=1000, description="Max records to return.")
    ] = None


# =============================================================================
# 3. OUTPUT VIEWS  (curated agent-facing shape; the outputSchema source of truth)
# =============================================================================


# =============================================================================
# 4. SHAPERS  (deterministic SDK-dict -> view; THE design work)
# =============================================================================


def _records(response: Any) -> list[Any]:
    """Extract the SDK paginated ``records`` list, tolerating bare lists."""
    if hasattr(response, "records"):
        return response.records or []
    if isinstance(response, list):
        return response
    return []


def _pagination(args: BaseModel) -> dict[str, Any]:
    qp: dict[str, Any] = {}
    offset = getattr(args, "offset", None)
    limit = getattr(args, "limit", None)
    if offset is not None:
        qp["offset"] = offset
    if limit is not None:
        qp["limit"] = limit
    return qp


# =============================================================================
# 2. TOOL FUNCTIONS  (input -> SDK call -> shaper -> curated output)
# =============================================================================


@tool(
    action=READ,
    service="zid",
    toolset="zid_groups",
    input_model=ListGroupsInput,
    is_list=True,
)
def zid_list_groups(args: ListGroupsInput) -> list[dict[str, Any]]:
    """List ZIdentity groups.

    Read-only. Returns lean group summaries (id, name, description, dynamic
    flag, source IdP) rather than the full SDK group record. Pass `name` for a
    case-insensitive partial-name filter.
    """
    client = get_zscaler_client(service="zid")
    api = client.zid.groups

    qp = _pagination(args)
    if args.name:
        qp["name[like]"] = args.name
    if args.exclude_dynamic_groups is not None:
        qp["exclude_dynamic_groups"] = args.exclude_dynamic_groups

    response, _, err = api.list_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list groups: {err}")

    return shape_many([g.as_dict() for g in _records(response)])


@tool(
    action=READ,
    service="zid",
    toolset="zid_groups",
    input_model=GetGroupInput,
    is_list=False,
)
def zid_get_group(args: GetGroupInput) -> dict[str, Any]:
    """Get one ZIdentity group by ID. Read-only."""
    if not args.group_id:
        raise ValueError("group_id is required")

    client = get_zscaler_client(service="zid")
    api = client.zid.groups

    group, _, err = api.get_group(args.group_id)
    if err:
        raise RuntimeError(f"Failed to fetch group {args.group_id}: {err}")

    return shape_one(group.as_dict())


@tool(
    action=READ,
    service="zid",
    toolset="zid_groups",
    input_model=SearchGroupsInput,
    is_list=True,
)
def zid_search_groups(args: SearchGroupsInput) -> list[dict[str, Any]]:
    """Search ZIdentity groups by name (case-insensitive partial match). Read-only.

    Returns curated group summaries. An empty result means no group name
    contains this string — do not retry with split keywords or no filter.
    """
    if not args.name:
        raise ValueError("name is required for search")

    client = get_zscaler_client(service="zid")
    api = client.zid.groups

    qp = _pagination(args)
    qp["name[like]"] = args.name

    response, _, err = api.list_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to search groups: {err}")

    return shape_many([g.as_dict() for g in _records(response)])


@tool(
    action=READ,
    service="zid",
    toolset="zid_groups",
    input_model=GroupUsersInput,
    is_list=True,
)
def zid_get_group_users(args: GroupUsersInput) -> list[dict[str, Any]]:
    """List the users that belong to a ZIdentity group, by group ID. Read-only.

    Returns lean user summaries (id, login name, display name, primary email)
    for each member of the group.
    """
    if not args.group_id:
        raise ValueError("group_id is required")

    client = get_zscaler_client(service="zid")
    api = client.zid.groups

    response, _, err = api.list_group_users_details(args.group_id, query_params=_pagination(args))
    if err:
        raise RuntimeError(f"Failed to fetch users for group {args.group_id}: {err}")

    return shape_many([u.as_dict() for u in _records(response)])


@tool(
    action=READ,
    service="zid",
    toolset="zid_groups",
    input_model=GroupUsersByNameInput,
    is_list=True,
)
def zid_get_group_users_by_name(args: GroupUsersByNameInput) -> list[dict[str, Any]]:
    """List the users in a ZIdentity group resolved by group name. Read-only.

    Resolves the group by case-insensitive partial name first, then returns the
    lean user summaries for the first matching group's members.
    """
    if not args.name:
        raise ValueError("name is required")

    client = get_zscaler_client(service="zid")
    api = client.zid.groups

    search_params = _pagination(args)
    search_params["name[like]"] = args.name

    groups_response, _, err = api.list_groups(query_params=search_params)
    if err:
        raise RuntimeError(f"Failed to search for group '{args.name}': {err}")

    groups = _records(groups_response)
    if not groups:
        raise ValueError(f"Group '{args.name}' not found")

    group_id = groups[0].id

    users_response, _, err = api.list_group_users_details(group_id, query_params=_pagination(args))
    if err:
        raise RuntimeError(f"Failed to fetch users for group '{args.name}' (ID: {group_id}): {err}")

    return shape_many([u.as_dict() for u in _records(users_response)])


# NOTE: no manual tool list — each function self-registers via @tool at import
# time (DESIGN.md §6).
