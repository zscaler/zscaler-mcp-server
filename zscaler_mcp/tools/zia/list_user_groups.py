from typing import Annotated, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# Maximum page_size accepted by the ZIA list_groups endpoint.
# Used internally when `name` is provided so we can pull a wide page
# and do client-side normalized matching without making the agent
# wrestle with pagination.
_MAX_PAGE_SIZE = 1000


def zia_user_group_manager(
    action: Annotated[
        Literal["read"],
        Field(
            description="Operation to perform. Use 'read' to paginate/filter groups or fetch a single group by ID."
        ),
    ] = "read",
    group_id: Annotated[
        Optional[Union[int, str]],
        Field(
            description="ID of the user group. When provided, returns a single group; otherwise returns a list of groups."
        ),
    ] = None,
    name: Annotated[
        Optional[str],
        Field(
            description=(
                "Case-insensitive substring match on the group's name field. "
                "Resolved client-side AFTER fetching the full group list, so "
                "names like 'A000', 'a000', 'HR', 'finance' all match "
                "regardless of the underlying name's casing. Use this when you "
                "have a literal group name from the admin and just need to "
                "find its ID. The server-side `search` parameter is unreliable "
                "for groups (it sometimes matches user login IDs instead of "
                "group names) — prefer `name` for find-by-name workflows."
            )
        ),
    ] = None,
    search: Annotated[
        Optional[str],
        Field(
            description=(
                "Server-side query forwarded to the ZIA list_groups endpoint. "
                "ZIA's documented behavior here is unreliable (the API has "
                "been observed to match against user login IDs rather than "
                "group names). Prefer `name` for case-insensitive substring "
                "matching on the group's name. Use `search` only when you "
                "specifically need the server-side semantics."
            )
        ),
    ] = None,
    defined_by: Annotated[
        Optional[str],
        Field(
            description="String value defined by the group name or other applicable attributes. Used to further filter results."
        ),
    ] = None,
    page: Annotated[
        Optional[int],
        Field(description="Page offset for pagination when listing groups."),
    ] = None,
    page_size: Annotated[
        Optional[int],
        Field(description="Page size for listing groups. Default is 100; maximum is 1000."),
    ] = None,
    sort_by: Annotated[
        Optional[Literal["id", "name", "expiry", "status", "external_id", "rank", "mod_time"]],
        Field(
            description="Sort field for listing groups. Supported: id, name, expiry, status, external_id, rank, mod_time."
        ),
    ] = None,
    sort_order: Annotated[
        Optional[Literal["asc", "desc", "rule_execution"]],
        Field(description="Sort order for listing groups. Supported: asc, desc, rule_execution."),
    ] = None,
    service: Annotated[
        str, Field(description="Zscaler service name. Always 'zia' for this tool.")
    ] = "zia",
) -> Union[dict, List[dict]]:
    """ZIA User Groups manager (read-only) using the Python SDK.

    This tool exposes read operations for ZIA User Groups via the SDK methods
    ``list_groups(query_params)`` and ``get_group(group_id)``.

    Lookup semantics:

    - ``group_id`` → fetch a single group by ID. Highest precedence.
    - ``name`` → fetch all groups (paginated server-side at 1000/page) and
      filter **client-side** by case-insensitive substring match on the
      ``name`` field. This bypasses the unreliable server-side ``search``
      behavior. Recommended for find-by-name workflows where the admin gives
      a literal group name like "A000" or "Finance".
    - ``search`` / ``defined_by`` → forwarded to the ZIA API. Use only when
      you specifically need server-side semantics. Note: ZIA's ``search`` on
      this endpoint has been observed to match against user login IDs
      rather than group names, so empty results may not mean "no group with
      this name exists".
    - No filters → list all groups (paginated).

    Returns:
        - Single dict when ``group_id`` is provided.
        - List of dicts otherwise.

    Examples:

        Find a group by literal admin-supplied name (most common):

        >>> zia_user_group_manager(action="read", name="A000")

        Get a single group by ID:

        >>> zia_user_group_manager(action="read", group_id="545225")

        List with sort:

        >>> zia_user_group_manager(action="read", page_size=500, sort_by="name", sort_order="asc")
    """
    client = get_zscaler_client(service=service)
    zia = client.zia.user_management

    if action != "read":
        raise ValueError(f"Unsupported action: {action}")

    if group_id is not None:
        group, _, err = zia.get_group(group_id)
        if err:
            raise Exception(f"Error retrieving user group {group_id}: {err}")
        return group.as_dict()

    if name is not None and not str(name).strip():
        raise ValueError("`name` must be a non-empty string when provided.")

    query_params: dict = {}

    # When `name` is supplied we deliberately skip the server-side `search`
    # parameter (its behavior on this endpoint is unreliable) and pull the
    # widest page we can so the client-side substring match is authoritative.
    if name is not None:
        query_params["page_size"] = _MAX_PAGE_SIZE
    else:
        if search is not None:
            query_params["search"] = search
        if defined_by is not None:
            query_params["defined_by"] = defined_by
        if page is not None:
            query_params["page"] = page
        if page_size is not None:
            if page_size <= 0:
                raise ValueError("page_size must be a positive integer")
            if page_size > _MAX_PAGE_SIZE:
                raise ValueError(f"page_size cannot exceed {_MAX_PAGE_SIZE}")
            query_params["page_size"] = page_size
        if sort_by is not None:
            query_params["sort_by"] = sort_by
        if sort_order is not None:
            query_params["sort_order"] = sort_order

    groups, _, err = zia.list_groups(query_params=query_params or None)
    if err:
        raise Exception(f"Error listing user groups: {err}")

    results = [g.as_dict() for g in (groups or [])]

    if name is not None:
        needle = str(name).strip().lower()
        results = [
            g for g in results
            if needle in str(g.get("name", "")).lower()
        ]

    return results
