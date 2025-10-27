import json
from typing import Annotated, Dict, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zia_list_ip_source_groups(
    search: Annotated[Optional[str], Field(description="Optional search string for filtering list results.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict]:
    """List ZIA IP source groups with optional filtering."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall
    
    query_params = {"search": search} if search else {}
    groups, _, err = zia.list_ip_source_groups(query_params=query_params)
    if err:
        raise Exception(f"Error listing IP source groups: {err}")
    return [g.as_dict() for g in groups]


def zia_get_ip_source_group(
    group_id: Annotated[Union[int, str], Field(description="Group ID for the IP source group.")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Get a specific ZIA IP source group by ID."""
    if not group_id:
        raise ValueError("group_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall
    
    group, _, err = zia.get_ip_source_group(group_id)
    if err:
        raise Exception(f"Error retrieving IP source group {group_id}: {err}")
    return group.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zia_create_ip_source_group(
    name: Annotated[str, Field(description="Group name (required).")],
    ip_addresses: Annotated[Union[List[str], str], Field(description="List of IP addresses (required). Accepts JSON string or list.")],
    description: Annotated[Optional[str], Field(description="Group description (optional).")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Create a new ZIA IP source group."""
    if not name or not ip_addresses:
        raise ValueError("Both name and ip_addresses are required")
    
    # Normalize IPs
    if isinstance(ip_addresses, str):
        try:
            ip_addresses = json.loads(ip_addresses)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for ip_addresses: {e}")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall
    
    group, _, err = zia.add_ip_source_group(name=name, description=description, ip_addresses=ip_addresses)
    if err:
        raise Exception(f"Error adding IP source group: {err}")
    return group.as_dict()


def zia_update_ip_source_group(
    group_id: Annotated[Union[int, str], Field(description="Group ID (required).")],
    name: Annotated[str, Field(description="Group name (required).")],
    ip_addresses: Annotated[Union[List[str], str], Field(description="List of IP addresses (required). Accepts JSON string or list.")],
    description: Annotated[Optional[str], Field(description="Group description (optional).")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Update an existing ZIA IP source group."""
    if not group_id or not name or not ip_addresses:
        raise ValueError("group_id, name, and ip_addresses are required for update")
    
    # Normalize IPs
    if isinstance(ip_addresses, str):
        try:
            ip_addresses = json.loads(ip_addresses)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for ip_addresses: {e}")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall
    
    group, _, err = zia.update_ip_source_group(
        group_id=group_id, name=name, description=description, ip_addresses=ip_addresses
    )
    if err:
        raise Exception(f"Error updating IP source group: {err}")
    return group.as_dict()


def zia_delete_ip_source_group(
    group_id: Annotated[Union[int, str], Field(description="Group ID (required).")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}"
) -> str:
    """Delete a ZIA IP source group."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zia_delete_ip_source_group",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not group_id:
        raise ValueError("group_id is required for delete")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall
    
    _, _, err = zia.delete_ip_source_group(group_id)
    if err:
        raise Exception(f"Error deleting IP source group {group_id}: {err}")
    return f"Group {group_id} deleted successfully"
