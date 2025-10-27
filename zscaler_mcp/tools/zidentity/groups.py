from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zidentity_list_groups(
    query_params: Annotated[Optional[Dict], Field(description="Optional filters: offset, limit, name[like], exclude_dynamic_groups.")] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zidentity",
) -> List[Dict]:
    """List Zidentity groups with optional filtering and pagination."""
    client = get_zscaler_client(service=service)
    api = client.zidentity.groups
    
    query_params = query_params or {}
    groups_response, _, err = api.list_groups(query_params=query_params)
    if err:
        raise Exception(f"Failed to list groups: {err}")
    
    groups = groups_response.records if hasattr(groups_response, 'records') else []
    return [group.as_dict() for group in groups]


def zidentity_get_group(
    group_id: Annotated[str, Field(description="Group ID.")],
    service: Annotated[str, Field(description="The service to use.")] = "zidentity",
) -> Dict:
    """Get a specific Zidentity group by ID."""
    if not group_id:
        raise ValueError("group_id is required")
    
    client = get_zscaler_client(service=service)
    api = client.zidentity.groups
    
    group, _, err = api.get_group(group_id)
    if err:
        raise Exception(f"Failed to fetch group {group_id}: {err}")
    return group.as_dict()


def zidentity_search_groups(
    name: Annotated[str, Field(description="Group name to search for (case-insensitive partial match).")],
    query_params: Annotated[Optional[Dict], Field(description="Optional filters for pagination.")] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zidentity",
) -> List[Dict]:
    """Search Zidentity groups by name using case-insensitive partial match."""
    if not name:
        raise ValueError("name is required for search")
    
    client = get_zscaler_client(service=service)
    api = client.zidentity.groups
    
    query_params = query_params or {}
    query_params["name[like]"] = name
    groups_response, _, err = api.list_groups(query_params=query_params)
    if err:
        raise Exception(f"Failed to search groups: {err}")
    
    groups = groups_response.records if hasattr(groups_response, 'records') else []
    return [group.as_dict() for group in groups]


def zidentity_get_group_users(
    group_id: Annotated[str, Field(description="Group ID.")],
    query_params: Annotated[Optional[Dict], Field(description="Optional filters: offset, limit, login_name, login_name[like], display_name[like], primary_email[like], domain_name, idp_name.")] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zidentity",
) -> List[Dict]:
    """Get users in a specific Zidentity group by group ID."""
    if not group_id:
        raise ValueError("group_id is required")
    
    client = get_zscaler_client(service=service)
    api = client.zidentity.groups
    
    query_params = query_params or {}
    users_response, _, err = api.list_group_users_details(group_id, query_params=query_params)
    if err:
        raise Exception(f"Failed to fetch users for group {group_id}: {err}")
    
    users = users_response.records if hasattr(users_response, 'records') else []
    return [user.as_dict() for user in users]


def zidentity_get_group_users_by_name(
    name: Annotated[str, Field(description="Group name to search for.")],
    query_params: Annotated[Optional[Dict], Field(description="Optional filters for pagination.")] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zidentity",
) -> List[Dict]:
    """Get users in a specific Zidentity group by group name (searches for group first)."""
    if not name:
        raise ValueError("name is required")
    
    client = get_zscaler_client(service=service)
    api = client.zidentity.groups
    
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
    
    users = users_response.records if hasattr(users_response, 'records') else []
    return [user.as_dict() for user in users]
