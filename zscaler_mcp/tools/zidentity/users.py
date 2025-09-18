from typing import Annotated, List, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def users_manager(
    action: Annotated[
        str,
        Field(description="Action to perform: 'read' (list users or get specific user by ID), 'get_groups' (get groups for a user by ID), 'get_groups_by_name' (get groups for a user by name), or 'search' (search users by name/email).")
    ] = "read",
    user_id: Annotated[
        str,
        Field(description="User ID for direct lookup or to get groups for the user.")
    ] = None,
    name: Annotated[
        str,
        Field(description="User name, login name, or email to search for (case-insensitive partial match).")
    ] = None,
    query_params: Annotated[
        dict,
        Field(description="Optional filters for pagination and filtering. For list_users: offset, limit, login_name, login_name[like], display_name[like], primary_email[like], domain_name, idp_name. For get_groups: offset, limit.")
    ] = None,
    service: Annotated[
        str,
        Field(description="The service to use.")
    ] = "zidentity",
) -> Union[dict, List[dict], str]:
    """
    Tool for managing Zidentity users.

    Supported actions:
    - read: Fetch all users with optional pagination and filtering, or a specific user by ID
    - get_groups: Get groups for a specific user by user ID
    - get_groups_by_name: Get groups for a specific user by user name/email (searches for user first)
    - search: Search users by name, login name, or email using case-insensitive partial match

    Available filtering parameters:
    - For list_users: offset, limit, login_name, login_name[like], display_name[like], primary_email[like], domain_name, idp_name
    - For get_groups: offset, limit

    Args:
        action (str): Action to perform ('read', 'get_groups', 'get_groups_by_name', 'search')
        user_id (str): User ID for direct lookup or to get groups for the user
        name (str): User name, login name, or email to search for (for 'search' or 'get_groups_by_name' action)
        query_params (dict): Optional filters for pagination and filtering
        service (str): The service to use (default: "zidentity")

    Returns:
        dict | list[dict] | str: User data or list of users/groups
    """
    client = get_zscaler_client(service=service)
    api = client.zidentity.users

    if action == "read":
        # If user_id is provided, get a specific user by ID
        if user_id:
            user, _, err = api.get_user(user_id)
            if err:
                raise Exception(f"Failed to fetch user {user_id}: {err}")
            return user.as_dict()
        else:
            # Otherwise, list all users with optional query parameters
            query_params = query_params or {}
            users_response, _, err = api.list_users(query_params=query_params)
            if err:
                raise Exception(f"Failed to list users: {err}")

            # Access the records field from the response object
            users = users_response.records if hasattr(users_response, 'records') else []
            return [user.as_dict() for user in users]

    elif action == "get_groups":
        # Get groups for a specific user by ID
        if not user_id:
            raise ValueError("user_id is required for 'get_groups' action")

        query_params = query_params or {}
        groups_response, _, err = api.list_user_group_details(user_id, query_params=query_params)
        if err:
            raise Exception(f"Failed to fetch groups for user {user_id}: {err}")

        # Note: list_user_group_details returns a list directly, not a response object
        return [group.as_dict() for group in groups_response]

    elif action == "get_groups_by_name":
        # Get groups for a specific user by name/email (searches for user first)
        if not name:
            raise ValueError("name is required for 'get_groups_by_name' action")

        # Search for the user by name using multiple possible filters
        search_params = query_params or {}

        # Try different search strategies based on the input
        if '@' in name:
            # If it contains @, treat as email
            search_params["primary_email[like]"] = name
        else:
            # Try login name first, then display name
            search_params["login_name[like]"] = name

        users_response, _, err = api.list_users(query_params=search_params)
        if err:
            raise Exception(f"Failed to search for user '{name}': {err}")

        users = users_response.records if hasattr(users_response, 'records') else []

        if not users:
            # If no results with login_name, try display_name
            search_params.pop("login_name[like]", None)
            search_params["display_name[like]"] = name

            users_response, _, err = api.list_users(query_params=search_params)
            if err:
                raise Exception(f"Failed to search for user '{name}': {err}")

            users = users_response.records if hasattr(users_response, 'records') else []

        if not users:
            raise ValueError(f"User '{name}' not found")

        # Use the first matching user's ID
        user_id = users[0].id

        # Now get groups using the found user ID
        group_query_params = query_params or {}
        # Remove search parameters as they're not valid for group queries
        for key in ["login_name[like]", "display_name[like]", "primary_email[like]"]:
            group_query_params.pop(key, None)

        groups_response, _, err = api.list_user_group_details(user_id, query_params=group_query_params)
        if err:
            raise Exception(f"Failed to fetch groups for user '{name}' (ID: {user_id}): {err}")

        # Note: list_user_group_details returns a list directly, not a response object
        return [group.as_dict() for group in groups_response]

    elif action == "search":
        # Search users by name, login name, or email using case-insensitive partial match
        if not name:
            raise ValueError("name is required for 'search' action")

        query_params = query_params or {}

        # Try different search strategies based on the input
        if '@' in name:
            # If it contains @, treat as email
            query_params["primary_email[like]"] = name
        else:
            # Try login name first
            query_params["login_name[like]"] = name

        users_response, _, err = api.list_users(query_params=query_params)
        if err:
            raise Exception(f"Failed to search users: {err}")

        # Access the records field from the response object
        users = users_response.records if hasattr(users_response, 'records') else []

        # If no results with login_name and input doesn't contain @, try display_name
        if not users and '@' not in name:
            query_params.pop("login_name[like]", None)
            query_params["display_name[like]"] = name

            users_response, _, err = api.list_users(query_params=query_params)
            if err:
                raise Exception(f"Failed to search users: {err}")

            users = users_response.records if hasattr(users_response, 'records') else []

        return [user.as_dict() for user in users]

    else:
        raise ValueError(f"Unsupported action: {action}. Supported actions are: 'read', 'get_groups', 'get_groups_by_name', 'search'")
