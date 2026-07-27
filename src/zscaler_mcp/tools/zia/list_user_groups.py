"""ZIA user groups — read-only manager.

Mirrors v1's ``list_user_groups.py`` exactly: a single multiplexed read tool
registered under the v1 name ``get_zia_user_groups`` (fetch by ID, find by name via
client-side substring match, or list with optional filters/sorting). Backed by
``client.zia.user_management``.

The group records are returned exactly as the ZIA API provides them
instead of the raw SDK dict, to keep token usage low.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many

# Maximum page_size accepted by the ZIA list_groups endpoint. Used when `name` is
# provided so we can pull a wide page and do client-side normalized matching.
_MAX_PAGE_SIZE = 1000


class GroupInput(BaseModel):
    """Inputs for reading ZIA user groups.

    Provide nothing to list all; provide ``group_id`` to fetch one (returned as a
    single-item list); provide ``name`` for a case-insensitive substring match
    resolved client-side (more reliable than the server-side ``search`` here).
    """

    group_id: Annotated[
        Optional[str], Field(default=None, description="Group ID for direct lookup.")
    ] = None
    name: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Case-insensitive substring match on group name (resolved client-side).",
        ),
    ] = None
    search: Annotated[
        Optional[str],
        Field(default=None, description="Server-side query (unreliable; prefer `name`)."),
    ] = None
    defined_by: Annotated[
        Optional[str], Field(default=None, description="Additional server-side filter.")
    ] = None
    page: Annotated[Optional[int], Field(default=None, description="Page number.")] = None
    page_size: Annotated[
        Optional[int], Field(default=None, description="Items per page (max 1000).")
    ] = None
    sort_by: Annotated[
        Optional[Literal["id", "name", "expiry", "status", "external_id", "rank", "mod_time"]],
        Field(default=None, description="Sort field."),
    ] = None
    sort_order: Annotated[
        Optional[Literal["asc", "desc", "rule_execution"]],
        Field(default=None, description="Sort order."),
    ] = None


@tool(
    action=READ,
    service="zia",
    toolset="zia_users",
    input_model=GroupInput,
    is_list=True,
)
def get_zia_user_groups(args: GroupInput) -> list[dict[str, Any]]:
    """Read ZIA user groups: fetch by ID, find by name, or list (read-only)."""
    client = get_zscaler_client(service="zia")
    api = client.zia.user_management

    if args.group_id:
        group, _, err = api.get_group(args.group_id)
        if err:
            raise RuntimeError(f"Failed to get user group {args.group_id}: {err}")
        return shape_many([group.as_dict()])

    if args.name is not None and not args.name.strip():
        raise ValueError("`name` must be a non-empty string when provided.")

    qp: dict[str, Any] = {}
    if args.name is not None:
        # Skip the unreliable server-side `search`; pull a wide page and match locally.
        qp["page_size"] = _MAX_PAGE_SIZE
    else:
        if args.search is not None:
            qp["search"] = args.search
        if args.defined_by is not None:
            qp["defined_by"] = args.defined_by
        if args.page is not None:
            qp["page"] = args.page
        if args.page_size is not None:
            if args.page_size <= 0 or args.page_size > _MAX_PAGE_SIZE:
                raise ValueError(f"page_size must be between 1 and {_MAX_PAGE_SIZE}")
            qp["page_size"] = args.page_size
        if args.sort_by is not None:
            qp["sort_by"] = args.sort_by
        if args.sort_order is not None:
            qp["sort_order"] = args.sort_order

    groups, _, err = api.list_groups(query_params=qp or None)
    if err:
        raise RuntimeError(f"Failed to list user groups: {err}")
    results = [g.as_dict() for g in (groups or [])]

    if args.name is not None:
        needle = args.name.strip().lower()
        results = [g for g in results if needle in str(g.get("name", "")).lower()]

    return shape_many(results)
