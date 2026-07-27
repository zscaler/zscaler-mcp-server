"""ZIdentity (ZID) users — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zid/users.py`` but adds the v2 shaping layer:
the verbose SDK user / group-membership records are curated down to the
identifying + relational subset an admin actually reasons about. See
DESIGN.md §5.

v1 exposed a free-form ``query_params`` dict plus a JMESPath ``query`` knob; v2
declares typed inputs and a curated, schema-backed output view instead. The
``UserSummary`` and ``GroupSummary`` views are shared with the groups module so
the agent sees one consistent shape regardless of entry point.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many, shape_one

# Shared, full records + shapers live with the groups module; reuse them so a
# user looks the same whether listed directly or via a group's membership, and
# a group looks the same whether listed directly or via a user's memberships.
from zscaler_mcp.tools.zid.groups import (
    _records,
)

# =============================================================================
# 1. INPUT MODELS  (typed + validated; the inputSchema source of truth)
# =============================================================================


class ListUsersInput(BaseModel):
    """Inputs for listing ZIdentity users."""

    login_name: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                "Case-insensitive partial match on the user's login name "
                "(server-side `login_name[like]` filter)."
            ),
        ),
    ] = None
    display_name: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Case-insensitive partial match on the user's display name.",
        ),
    ] = None
    primary_email: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Case-insensitive partial match on the user's primary email.",
        ),
    ] = None
    domain_name: Annotated[
        Optional[str], Field(default=None, description="Exact domain-name filter.")
    ] = None
    idp_name: Annotated[
        Optional[str], Field(default=None, description="Exact identity-provider-name filter.")
    ] = None
    offset: Annotated[
        Optional[int], Field(default=None, ge=0, description="Pagination offset (records to skip).")
    ] = None
    limit: Annotated[
        Optional[int], Field(default=None, ge=1, le=1000, description="Max records to return.")
    ] = None


class GetUserInput(BaseModel):
    """Inputs for getting one ZIdentity user."""

    user_id: Annotated[str, Field(description="ID of the user (string, even if numeric).")]


class SearchUsersInput(BaseModel):
    """Inputs for searching ZIdentity users by name, login name, or email."""

    name: Annotated[
        str,
        Field(
            description=(
                "User name, login name, or email to search for (case-insensitive "
                "partial match). Values containing '@' are matched against email; "
                "otherwise login name then display name are tried."
            )
        ),
    ]
    offset: Annotated[
        Optional[int], Field(default=None, ge=0, description="Pagination offset (records to skip).")
    ] = None
    limit: Annotated[
        Optional[int], Field(default=None, ge=1, le=1000, description="Max records to return.")
    ] = None


class UserGroupsInput(BaseModel):
    """Inputs for listing the groups a ZIdentity user belongs to, by user ID."""

    user_id: Annotated[str, Field(description="ID of the user (string, even if numeric).")]
    offset: Annotated[
        Optional[int], Field(default=None, ge=0, description="Pagination offset (records to skip).")
    ] = None
    limit: Annotated[
        Optional[int], Field(default=None, ge=1, le=1000, description="Max records to return.")
    ] = None


class UserGroupsByNameInput(BaseModel):
    """Inputs for listing a ZIdentity user's groups, resolving the user by name."""

    name: Annotated[
        str,
        Field(
            description=(
                "User name, login name, or email to resolve (case-insensitive "
                "partial match). The first matching user's group memberships are "
                "returned."
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
# 4. HELPERS  (search-filter selection mirrored from v1)
# =============================================================================


def _pagination(args: BaseModel) -> dict[str, Any]:
    qp: dict[str, Any] = {}
    offset = getattr(args, "offset", None)
    limit = getattr(args, "limit", None)
    if offset is not None:
        qp["offset"] = offset
    if limit is not None:
        qp["limit"] = limit
    return qp


def _search_users(api: Any, name: str, base_params: dict[str, Any]) -> list[Any]:
    """Search users mirroring v1's strategy: email when '@' present, else login
    name then display name."""
    params = dict(base_params)
    if "@" in name:
        params["primary_email[like]"] = name
    else:
        params["login_name[like]"] = name

    response, _, err = api.list_users(query_params=params)
    if err:
        raise RuntimeError(f"Failed to search users: {err}")

    users = _records(response)
    if not users and "@" not in name:
        params.pop("login_name[like]", None)
        params["display_name[like]"] = name
        response, _, err = api.list_users(query_params=params)
        if err:
            raise RuntimeError(f"Failed to search users: {err}")
        users = _records(response)

    return users


# =============================================================================
# 2. TOOL FUNCTIONS  (input -> SDK call -> shaper -> curated output)
# =============================================================================


@tool(
    action=READ,
    service="zid",
    toolset="zid_users",
    input_model=ListUsersInput,
    is_list=True,
)
def zid_list_users(args: ListUsersInput) -> list[dict[str, Any]]:
    """List ZIdentity users. Read-only.

    Returns lean user summaries (id, login name, display name, primary email)
    rather than the full SDK user record. Pass any of the `*_name` / email
    filters for a case-insensitive partial match.
    """
    client = get_zscaler_client(service="zid")
    api = client.zid.users

    qp = _pagination(args)
    if args.login_name:
        qp["login_name[like]"] = args.login_name
    if args.display_name:
        qp["display_name[like]"] = args.display_name
    if args.primary_email:
        qp["primary_email[like]"] = args.primary_email
    if args.domain_name:
        qp["domain_name"] = args.domain_name
    if args.idp_name:
        qp["idp_name"] = args.idp_name

    response, _, err = api.list_users(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list users: {err}")

    return shape_many([u.as_dict() for u in _records(response)])


@tool(
    action=READ,
    service="zid",
    toolset="zid_users",
    input_model=GetUserInput,
    is_list=False,
)
def zid_get_user(args: GetUserInput) -> dict[str, Any]:
    """Get one ZIdentity user by ID. Read-only."""
    if not args.user_id:
        raise ValueError("user_id is required")

    client = get_zscaler_client(service="zid")
    api = client.zid.users

    user, _, err = api.get_user(args.user_id)
    if err:
        raise RuntimeError(f"Failed to fetch user {args.user_id}: {err}")

    return shape_one(user.as_dict())


@tool(
    action=READ,
    service="zid",
    toolset="zid_users",
    input_model=SearchUsersInput,
    is_list=True,
)
def zid_search_users(args: SearchUsersInput) -> list[dict[str, Any]]:
    """Search ZIdentity users by name, login name, or email. Read-only.

    Case-insensitive partial match. Values containing '@' match email;
    otherwise login name then display name are tried. An empty result means no
    user matches — do not retry with split keywords or no filter.
    """
    if not args.name:
        raise ValueError("name is required for search")

    client = get_zscaler_client(service="zid")
    api = client.zid.users

    users = _search_users(api, args.name, _pagination(args))
    return shape_many([u.as_dict() for u in users])


@tool(
    action=READ,
    service="zid",
    toolset="zid_users",
    input_model=UserGroupsInput,
    is_list=True,
)
def zid_get_user_groups(args: UserGroupsInput) -> list[dict[str, Any]]:
    """List the groups a ZIdentity user belongs to, by user ID. Read-only.

    Returns lean group summaries (id, name, description, dynamic flag, source
    IdP) for each of the user's group memberships.
    """
    if not args.user_id:
        raise ValueError("user_id is required")

    client = get_zscaler_client(service="zid")
    api = client.zid.users

    response, _, err = api.list_user_group_details(args.user_id, query_params=_pagination(args))
    if err:
        raise RuntimeError(f"Failed to fetch groups for user {args.user_id}: {err}")

    return shape_many([g.as_dict() for g in _records(response)])


@tool(
    action=READ,
    service="zid",
    toolset="zid_users",
    input_model=UserGroupsByNameInput,
    is_list=True,
)
def zid_get_user_groups_by_name(args: UserGroupsByNameInput) -> list[dict[str, Any]]:
    """List a ZIdentity user's group memberships, resolving the user by name.

    Read-only. Resolves the user by case-insensitive partial match (email when
    '@' present, else login then display name), then returns the lean group
    summaries for the first matching user's memberships.
    """
    if not args.name:
        raise ValueError("name is required")

    client = get_zscaler_client(service="zid")
    api = client.zid.users

    users = _search_users(api, args.name, _pagination(args))
    if not users:
        raise ValueError(f"User '{args.name}' not found")

    user_id = users[0].id

    response, _, err = api.list_user_group_details(user_id, query_params=_pagination(args))
    if err:
        raise RuntimeError(f"Failed to fetch groups for user '{args.name}' (ID: {user_id}): {err}")

    return shape_many([g.as_dict() for g in _records(response)])


# NOTE: no manual tool list — each function self-registers via @tool at import
# time (DESIGN.md §6).
