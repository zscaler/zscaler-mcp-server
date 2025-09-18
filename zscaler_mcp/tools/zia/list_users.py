from typing import Annotated, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zia_users_manager(
    action: Annotated[
        Literal["read"],
        Field(description="Operation to perform. Use 'read' to paginate/filter users or fetch a single user by ID."),
    ] = "read",
    user_id: Annotated[
        Optional[Union[int, str]],
        Field(description="User ID. When provided, returns a single user; otherwise returns a list of users."),
    ] = None,
    dept: Annotated[
        Optional[str],
        Field(description="Filters by department name (starts with match)."),
    ] = None,
    group: Annotated[
        Optional[str],
        Field(description="Filters by group name (starts with match)."),
    ] = None,
    name: Annotated[
        Optional[str],
        Field(description="Filters by user name (starts with match)."),
    ] = None,
    page: Annotated[
        Optional[int],
        Field(description="Page offset for pagination when listing users."),
    ] = None,
    page_size: Annotated[
        Optional[int],
        Field(description="Page size for listing users. Default is 100; maximum is 1000."),
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API."),
    ] = False,
    service: Annotated[
        str, Field(description="Zscaler service name. Always 'zia' for this tool."),
    ] = "zia",
) -> Union[dict, List[dict]]:
    """
    ZIA Users manager using the Python SDK.

    This tool exposes read operations for ZIA Users via:
    - list_users(query_params)
    - get_user(user_id)

    Supported actions:
    - "read": Retrieves a paginated list of users with optional filters, or a single user if user_id is provided.

    Parameters:
    - action: Always "read" (default).
    - user_id: Optional. When provided, returns a single user; otherwise returns a list of users.
    - dept: Optional department name filter (starts with match).
    - group: Optional group name filter (starts with match).
    - name: Optional user name filter (starts with match).
    - page: Optional page offset for pagination.
    - page_size: Optional page size for pagination. Default 100; maximum 1000.
    - use_legacy: Whether to use the legacy client implementation.
    - service: Zscaler service. Use "zia".

    Returns:
    - List[dict] when user_id is not provided — each element represents a user as a dictionary.
    - dict when user_id is provided — the user represented as a dictionary.

    Examples:
    
    - List users filtered by department and group with pagination
      >>> zia_users_manager(
      ...     dept="Finance",
      ...     group="Corp-Users",
      ...     page=1,
      ...     page_size=200,
      ... )

    - List users with a name prefix and a strict page size
      >>> zia_users_manager(name="john", page_size=10)

    - Get a user by ID
      >>> zia_users_manager(user_id=123456)
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.user_management

    if action == "read":
        # If user_id is provided, get a single user
        if user_id is not None:
            user, _, err = zia.get_user(user_id)
            if err:
                raise Exception(f"Error retrieving user {user_id}: {err}")
            return user.as_dict()
        
        # Otherwise, list users with optional filters
        query_params = {}
        if dept is not None:
            query_params["dept"] = dept
        if group is not None:
            query_params["group"] = group
        if name is not None:
            query_params["name"] = name
        if page is not None:
            query_params["page"] = page
        if page_size is not None:
            if page_size <= 0:
                raise ValueError("page_size must be a positive integer")
            if page_size > 1000:
                raise ValueError("page_size cannot exceed 1000")
            query_params["page_size"] = page_size

        users, _, err = zia.list_users(query_params=query_params or None)
        if err:
            raise Exception(f"Error listing users: {err}")
        return [u.as_dict() for u in users]

    raise ValueError(f"Unsupported action: {action}")
