from typing import Annotated, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zia_user_group_manager(
    action: Annotated[
        Literal["list", "read"],
        Field(description="Which operation to perform. Use 'list' to paginate/filter groups or 'read' to fetch a single group by ID."),
    ] = "list",
    group_id: Annotated[
        Optional[Union[int, str]],
        Field(description="ID of the user group. Required when action is 'read'."),
    ] = None,
    search: Annotated[
        Optional[str],
        Field(description="Search string to match against a group's name or other applicable attributes."),
    ] = None,
    defined_by: Annotated[
        Optional[str],
        Field(description="String value defined by the group name or other applicable attributes. Used to further filter results."),
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
        Field(description="Sort field for listing groups. Supported: id, name, expiry, status, external_id, rank, mod_time."),
    ] = None,
    sort_order: Annotated[
        Optional[Literal["asc", "desc", "rule_execution"]],
        Field(description="Sort order for listing groups. Supported: asc, desc, rule_execution."),
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="Zscaler service name. Always 'zia' for this tool.")] = "zia",
) -> Union[dict, List[dict]]:
    """
    ZIA User Groups manager using the Python SDK.

    This tool exposes read operations for ZIA User Groups via the SDK methods
    `list_groups(query_params)` and `get_group(group_id)`.

    Supported actions
    - "list": Retrieves a paginated list of user groups with optional filters and sorting.
    - "get": Retrieves a single user group by its unique identifier.

    Parameters
    - action: One of ["list", "get"]. Defaults to "list".
    - group_id: Required when action is "get". The unique user group ID (int or str).
    - search: Optional search string to match against a group's name or other applicable attributes.
    - defined_by: Optional string filter defined by the group name or applicable attributes.
    - page: Optional page offset for pagination.
    - page_size: Optional page size for pagination. The SDK's default is 100; maximum is 1000.
    - sort_by: Optional sort field. Supported values: "id", "name", "expiry", "status", "external_id", "rank", "mod_time".
    - sort_order: Optional sort order. Supported values: "asc", "desc", "rule_execution".
    - use_legacy: Whether to use the legacy client implementation.
    - service: Zscaler service. Use "zia".

    Returns
    - For action "list": List[dict] — each element represents a user group as a dictionary.
    - For action "get": dict — the user group represented as a dictionary.

    Examples
    - List groups with larger page size and by name search
      >>> zia_user_group_manager(
      ...     action="list",
      ...     search="Engineering",
      ...     page=1,
      ...     page_size=500,
      ...     sort_by="name",
      ...     sort_order="asc",
      ... )

    - Get a single group by ID
      >>> zia_user_group_manager(action="get", group_id="545225")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.user_management

    if action == "list":
        query_params = {}
        if search is not None:
            query_params["search"] = search
        if defined_by is not None:
            query_params["defined_by"] = defined_by
        if page is not None:
            query_params["page"] = page
        if page_size is not None:
            if page_size <= 0:
                raise ValueError("page_size must be a positive integer")
            if page_size > 1000:
                raise ValueError("page_size cannot exceed 1000")
            query_params["page_size"] = page_size
        if sort_by is not None:
            query_params["sort_by"] = sort_by
        if sort_order is not None:
            query_params["sort_order"] = sort_order

        groups, _, err = zia.list_groups(query_params=query_params or None)
        if err:
            raise Exception(f"Error listing user groups: {err}")
        return [g.as_dict() for g in groups]

    if action == "read":
        if not group_id:
            raise ValueError("group_id is required for action 'read'")
        group, _, err = zia.get_group(group_id)
        if err:
            raise Exception(f"Error retrieving user group {group_id}: {err}")
        return group.as_dict()

    raise ValueError(f"Unsupported action: {action}")
