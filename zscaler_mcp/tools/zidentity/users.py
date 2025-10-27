from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zidentity_list_users(
    query_params: Annotated[Optional[Dict], Field(description="Optional filters: offset, limit, login_name, login_name[like], display_name[like], primary_email[like], domain_name, idp_name.")] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zidentity",
) -> List[Dict]:
    """List Zidentity users with optional filtering and pagination."""
    client = get_zscaler_client(service=service)
    api = client.zidentity.users
    
    query_params = query_params or {}
    users_response, _, err = api.list_users(query_params=query_params)
    if err:
        raise Exception(f"Failed to list users: {err}")
    
    users = users_response.records if hasattr(users_response, 'records') else []
    return [user.as_dict() for user in users]


def zidentity_get_user(
    user_id: Annotated[str, Field(description="User ID.")],
    service: Annotated[str, Field(description="The service to use.")] = "zidentity",
) -> Dict:
    """Get a specific Zidentity user by ID."""
    if not user_id:
        raise ValueError("user_id is required")
    
    client = get_zscaler_client(service=service)
    api = client.zidentity.users
    
    user, _, err = api.get_user(user_id)
    if err:
        raise Exception(f"Failed to fetch user {user_id}: {err}")
    return user.as_dict()


def zidentity_search_users(
    name: Annotated[str, Field(description="User name, login name, or email to search for (case-insensitive partial match).")],
    query_params: Annotated[Optional[Dict], Field(description="Optional filters for pagination.")] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zidentity",
) -> List[Dict]:
    """Search Zidentity users by name, login name, or email using case-insensitive partial match."""
    if not name:
        raise ValueError("name is required for search")
    
    client = get_zscaler_client(service=service)
    api = client.zidentity.users
    
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


def zidentity_get_user_groups(
    user_id: Annotated[str, Field(description="User ID.")],
    query_params: Annotated[Optional[Dict], Field(description="Optional filters: offset, limit.")] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zidentity",
) -> List[Dict]:
    """Get groups for a specific Zidentity user by user ID."""
    if not user_id:
        raise ValueError("user_id is required")
    
    client = get_zscaler_client(service=service)
    api = client.zidentity.users
    
    query_params = query_params or {}
    groups_response, _, err = api.list_user_group_details(user_id, query_params=query_params)
    if err:
        raise Exception(f"Failed to fetch groups for user {user_id}: {err}")
    
    return [group.as_dict() for group in groups_response]


def zidentity_get_user_groups_by_name(
    name: Annotated[str, Field(description="User name, login name, or email to search for.")],
    query_params: Annotated[Optional[Dict], Field(description="Optional filters for pagination.")] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zidentity",
) -> List[Dict]:
    """Get groups for a specific Zidentity user by name/email (searches for user first)."""
    if not name:
        raise ValueError("name is required")
    
    client = get_zscaler_client(service=service)
    api = client.zidentity.users
    
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
    
    return [group.as_dict() for group in groups_response]
