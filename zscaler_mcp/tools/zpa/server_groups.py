from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zpa_list_server_groups(
    search: Annotated[Optional[str], Field(description="Search term for filtering results.")] = None,
    page: Annotated[Optional[str], Field(description="Page number for pagination.")] = None,
    page_size: Annotated[Optional[str], Field(description="Number of items per page.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> List[Dict]:
    """List ZPA server groups with optional filtering and pagination."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.server_groups
    
    qp = {"microtenant_id": microtenant_id}
    if search:
        qp["search"] = search
    if page:
        qp["page"] = page
    if page_size:
        qp["page_size"] = page_size
    
    groups, _, err = api.list_groups(query_params=qp)
    if err:
        raise Exception(f"Failed to list server groups: {err}")
    return [g.as_dict() for g in (groups or [])]


def zpa_get_server_group(
    group_id: Annotated[str, Field(description="Group ID for the server group.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Get a specific ZPA server group by ID."""
    if not group_id:
        raise ValueError("group_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.server_groups
    
    group, _, err = api.get_group(group_id, query_params={"microtenant_id": microtenant_id})
    if err:
        raise Exception(f"Failed to get server group {group_id}: {err}")
    return group.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zpa_create_server_group(
    name: Annotated[str, Field(description="Name of the server group.")],
    app_connector_group_ids: Annotated[List[str], Field(description="List of app connector group IDs (required).")],
    description: Annotated[Optional[str], Field(description="Description of the server group.")] = None,
    enabled: Annotated[bool, Field(description="Whether the group is enabled.")] = True,
    server_ids: Annotated[Optional[List[str]], Field(description="List of server IDs.")] = None,
    ip_anchored: Annotated[Optional[bool], Field(description="Whether the group is IP anchored.")] = None,
    dynamic_discovery: Annotated[Optional[bool], Field(description="Whether dynamic discovery is enabled.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Create a new ZPA server group."""
    if not name or not app_connector_group_ids:
        raise ValueError("name and app_connector_group_ids are required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.server_groups
    
    body = {
        "name": name,
        "description": description,
        "enabled": enabled,
        "app_connector_group_ids": app_connector_group_ids or [],
        "server_ids": server_ids or [],
        "ip_anchored": ip_anchored,
        "dynamic_discovery": dynamic_discovery,
    }
    if microtenant_id:
        body["microtenant_id"] = microtenant_id
    
    created, _, err = api.add_group(**body)
    if err:
        raise Exception(f"Failed to create server group: {err}")
    return created.as_dict()


def zpa_update_server_group(
    group_id: Annotated[str, Field(description="Group ID for the server group.")],
    name: Annotated[Optional[str], Field(description="Name of the server group.")] = None,
    description: Annotated[Optional[str], Field(description="Description of the server group.")] = None,
    enabled: Annotated[Optional[bool], Field(description="Whether the group is enabled.")] = None,
    app_connector_group_ids: Annotated[Optional[List[str]], Field(description="List of app connector group IDs.")] = None,
    server_ids: Annotated[Optional[List[str]], Field(description="List of server IDs.")] = None,
    ip_anchored: Annotated[Optional[bool], Field(description="Whether the group is IP anchored.")] = None,
    dynamic_discovery: Annotated[Optional[bool], Field(description="Whether dynamic discovery is enabled.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Update an existing ZPA server group."""
    if not group_id:
        raise ValueError("group_id is required for update")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.server_groups
    
    body = {
        "name": name,
        "description": description,
        "enabled": enabled,
        "app_connector_group_ids": app_connector_group_ids or [],
        "server_ids": server_ids or [],
        "ip_anchored": ip_anchored,
        "dynamic_discovery": dynamic_discovery,
    }
    if microtenant_id:
        body["microtenant_id"] = microtenant_id
    
    updated, _, err = api.update_group(group_id, **body)
    if err:
        raise Exception(f"Failed to update server group {group_id}: {err}")
    return updated.as_dict()


def zpa_delete_server_group(
    group_id: Annotated[str, Field(description="Group ID for the server group.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}"
) -> str:
    """Delete a ZPA server group."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zpa_delete_server_group",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not group_id:
        raise ValueError("group_id is required for delete")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.server_groups
    
    _, _, err = api.delete_group(group_id, microtenant_id=microtenant_id)
    if err:
        raise Exception(f"Failed to delete server group {group_id}: {err}")
    return f"Successfully deleted server group {group_id}"
