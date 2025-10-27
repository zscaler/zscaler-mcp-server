from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zpa_list_application_servers(
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    query_params: Annotated[Optional[Dict], Field(description="Optional query parameters for filtering.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> List[Dict]:
    """List ZPA application servers with optional filtering."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.servers
    
    qp = query_params or {}
    if microtenant_id:
        qp["microtenant_id"] = microtenant_id
    
    servers, _, err = api.list_servers(query_params=qp)
    if err:
        raise Exception(f"Failed to list application servers: {err}")
    return [s.as_dict() for s in servers]


def zpa_get_application_server(
    server_id: Annotated[str, Field(description="Server ID for the application server.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Get a specific ZPA application server by ID."""
    if not server_id:
        raise ValueError("server_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.servers
    
    result, _, err = api.get_server(server_id, query_params={"microtenant_id": microtenant_id})
    if err:
        raise Exception(f"Failed to get application server {server_id}: {err}")
    return result.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zpa_create_application_server(
    name: Annotated[str, Field(description="Name of the application server.")],
    address: Annotated[str, Field(description="The domain or IP address of the server.")],
    description: Annotated[Optional[str], Field(description="Description of the application server.")] = None,
    enabled: Annotated[bool, Field(description="Whether the server is enabled.")] = True,
    app_server_group_ids: Annotated[Optional[List[str]], Field(description="List of server group IDs.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Create a new ZPA application server."""
    if not all([name, address]):
        raise ValueError("Both 'name' and 'address' are required for creation")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.servers
    
    payload = {
        "name": name,
        "description": description,
        "address": address,
        "enabled": enabled,
        "app_server_group_ids": app_server_group_ids,
    }
    if microtenant_id:
        payload["microtenant_id"] = microtenant_id
    
    created, _, err = api.add_server(**payload)
    if err:
        raise Exception(f"Failed to create application server: {err}")
    return created.as_dict()


def zpa_update_application_server(
    server_id: Annotated[str, Field(description="Server ID for the application server.")],
    name: Annotated[Optional[str], Field(description="Name of the application server.")] = None,
    address: Annotated[Optional[str], Field(description="The domain or IP address of the server.")] = None,
    description: Annotated[Optional[str], Field(description="Description of the application server.")] = None,
    enabled: Annotated[Optional[bool], Field(description="Whether the server is enabled.")] = None,
    app_server_group_ids: Annotated[Optional[List[str]], Field(description="List of server group IDs.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Update an existing ZPA application server."""
    if not server_id:
        raise ValueError("server_id is required for update")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.servers
    
    payload = {
        "name": name,
        "description": description,
        "address": address,
        "enabled": enabled,
        "app_server_group_ids": app_server_group_ids,
    }
    if microtenant_id:
        payload["microtenant_id"] = microtenant_id
    
    updated, _, err = api.update_server(server_id, **payload)
    if err:
        raise Exception(f"Failed to update application server {server_id}: {err}")
    return updated.as_dict()


def zpa_delete_application_server(
    server_id: Annotated[str, Field(description="Server ID for the application server.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}"
) -> str:
    """Delete a ZPA application server."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zpa_delete_application_server",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not server_id:
        raise ValueError("server_id is required for deletion")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.servers
    
    _, _, err = api.delete_server(server_id, microtenant_id=microtenant_id)
    if err:
        raise Exception(f"Failed to delete application server {server_id}: {err}")
    return f"Successfully deleted application server {server_id}"
