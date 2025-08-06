from zscaler_mcp.client import get_zscaler_client
from typing import Annotated, Union, List
from pydantic import Field


def groups_manager(
    action: Annotated[
        str,
        Field(description="Action to perform: 'list' (get all groups), 'get' (get specific group by ID), 'get_users' (get users in a group by ID), 'get_users_by_name' (get users in a group by name), or 'search' (search groups by name).")
    ],
    group_id: Annotated[
        str,
        Field(description="Group ID for direct lookup or to get users in the group.")
    ] = None,
    name: Annotated[
        str,
        Field(description="Group name to search for (case-insensitive partial match).")
    ] = None,
    query_params: Annotated[
        dict,
        Field(description="Optional filters for pagination and filtering. For list_groups: offset, limit, name[like], exclude_dynamic_groups. For get_users: offset, limit, login_name, login_name[like], display_name[like], primary_email[like], domain_name, idp_name.")
    ] = None,
    service: Annotated[
        str,
        Field(description="The service to use.")
    ] = "zidentity",
) -> Union[dict, List[dict], str]:
    """
    Tool for managing Zidentity groups.

    Supported actions:
    - list: Fetch all groups with optional pagination and filtering
    - get: Fetch a specific group by ID
    - get_users: Get users in a specific group by group ID
    - get_users_by_name: Get users in a specific group by group name (searches for group first)
    - search: Search groups by name using case-insensitive partial match

    Available filtering parameters:
    - For list_groups: offset, limit, name[like], exclude_dynamic_groups
    - For get_users: offset, limit, login_name, login_name[like], display_name[like], primary_email[like], domain_name, idp_name

    Args:
        action (str): Action to perform ('list', 'get', 'get_users', 'get_users_by_name', 'search')
        group_id (str): Group ID for direct lookup or to get users in the group
        name (str): Group name to search for (for 'search' or 'get_users_by_name' action)
        query_params (dict): Optional filters for pagination and filtering
        service (str): The service to use (default: "zidentity")

    Returns:
        dict | list[dict] | str: Group data or list of groups/users
    """
    client = get_zscaler_client(service=service)
    api = client.zidentity.groups

    if action == "list":
        # List all groups with optional query parameters
        query_params = query_params or {}
        groups_response, _, err = api.list_groups(query_params=query_params)
        if err:
            raise Exception(f"Failed to list groups: {err}")

        # Access the records field from the response object
        groups = groups_response.records if hasattr(groups_response, 'records') else []
        return [group.as_dict() for group in groups]

    elif action == "get":
        # Get a specific group by ID
        if not group_id:
            raise ValueError("group_id is required for 'get' action")

        group, _, err = api.get_group(group_id)
        if err:
            raise Exception(f"Failed to fetch group {group_id}: {err}")
        return group.as_dict()

    elif action == "get_users":
        # Get users in a specific group by ID
        if not group_id:
            raise ValueError("group_id is required for 'get_users' action")

        query_params = query_params or {}
        users_response, _, err = api.list_group_users_details(group_id, query_params=query_params)
        if err:
            raise Exception(f"Failed to fetch users for group {group_id}: {err}")

        # Access the records field from the response object
        users = users_response.records if hasattr(users_response, 'records') else []
        return [user.as_dict() for user in users]

    elif action == "get_users_by_name":
        # Get users in a specific group by name (searches for group first)
        if not name:
            raise ValueError("name is required for 'get_users_by_name' action")

        # Search for the group by name using the name[like] filter
        search_params = query_params or {}
        search_params["name[like]"] = name

        groups_response, _, err = api.list_groups(query_params=search_params)
        if err:
            raise Exception(f"Failed to search for group '{name}': {err}")

        groups = groups_response.records if hasattr(groups_response, 'records') else []

        if not groups:
            raise ValueError(f"Group '{name}' not found")

        # Use the first matching group's ID
        group_id = groups[0].id

        # Now get users using the found group ID
        user_query_params = query_params or {}
        # Remove the name[like] parameter as it's not valid for user queries
        user_query_params.pop("name[like]", None)

        users_response, _, err = api.list_group_users_details(group_id, query_params=user_query_params)
        if err:
            raise Exception(f"Failed to fetch users for group '{name}' (ID: {group_id}): {err}")

        # Access the records field from the response object
        users = users_response.records if hasattr(users_response, 'records') else []
        return [user.as_dict() for user in users]

    elif action == "search":
        # Search groups by name using case-insensitive partial match
        if not name:
            raise ValueError("name is required for 'search' action")

        query_params = query_params or {}
        query_params["name[like]"] = name
        groups_response, _, err = api.list_groups(query_params=query_params)
        if err:
            raise Exception(f"Failed to search groups: {err}")

        # Access the records field from the response object
        groups = groups_response.records if hasattr(groups_response, 'records') else []
        return [group.as_dict() for group in groups]

    else:
        raise ValueError(f"Unsupported action: {action}. Supported actions are: 'list', 'get', 'get_users', 'get_users_by_name', 'search'")