import json
from typing import Annotated, Dict, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def ztw_list_ip_groups(
    search: Annotated[Optional[str], Field(description="Optional search string for filtering list results.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
) -> List[Dict]:
    """List ZTW IP groups with optional search filtering."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    ztw = client.ztw.ip_groups
    
    query_params = {"search": search} if search else {}
    groups, _, err = ztw.list_ip_groups(query_params=query_params)
    if err:
        raise Exception(f"Error listing IP groups: {err}")
    return [g.as_dict() for g in groups]


def ztw_list_ip_groups_lite(
    search: Annotated[Optional[str], Field(description="Optional search string for filtering list results.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
) -> List[Dict]:
    """List ZTW IP groups (lightweight version) with optional search filtering."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    ztw = client.ztw.ip_groups
    
    query_params = {"search": search} if search else {}
    groups, _, err = ztw.list_ip_groups_lite(query_params=query_params)
    if err:
        raise Exception(f"Error listing IP groups (lite): {err}")
    return [g.as_dict() for g in groups]


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def ztw_create_ip_group(
    name: Annotated[str, Field(description="Group name (required).")],
    ip_addresses: Annotated[Union[List[str], str], Field(description="List of IP addresses (required). Accepts JSON string or list.")],
    description: Annotated[Optional[str], Field(description="Group description (optional).")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
) -> Dict:
    """Create a new ZTW IP group."""
    if not name or not ip_addresses:
        raise ValueError("Both name and ip_addresses are required")
    
    # Normalize IPs
    if isinstance(ip_addresses, str):
        try:
            ip_addresses = json.loads(ip_addresses)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for ip_addresses: {e}")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    ztw = client.ztw.ip_groups
    
    group, _, err = ztw.add_ip_group(name=name, description=description, ip_addresses=ip_addresses)
    if err:
        raise Exception(f"Error adding IP group: {err}")
    return group.as_dict()


def ztw_delete_ip_group(
    group_id: Annotated[Union[int, str], Field(description="Group ID (required).")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
    kwargs: str = "{}"
) -> str:
    """Delete a ZTW IP group.
    
    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "ztw_delete_ip_group",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not group_id:
        raise ValueError("group_id is required for delete")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    ztw = client.ztw.ip_groups
    
    _, _, err = ztw.delete_ip_group(group_id)
    if err:
        raise Exception(f"Error deleting IP group {group_id}: {err}")
    return f"Group {group_id} deleted successfully"
