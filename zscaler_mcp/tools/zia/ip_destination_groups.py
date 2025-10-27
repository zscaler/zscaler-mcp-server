import json
from typing import Annotated, Dict, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def _parse_list(val):
    """Helper to parse JSON string to list."""
    if isinstance(val, str):
        return json.loads(val)
    return val


# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zia_list_ip_destination_groups(
    exclude_type: Annotated[Optional[str], Field(description="Optional filter to exclude groups of type DSTN_IP, DSTN_FQDN, etc.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict]:
    """List ZIA IP destination groups with optional filtering."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall
    
    query_params = {"exclude_type": exclude_type} if exclude_type else {}
    groups, _, err = zia.list_ip_destination_groups(query_params=query_params)
    if err:
        raise Exception(f"Failed to list IP destination groups: {err}")
    return [g.as_dict() for g in groups]


def zia_get_ip_destination_group(
    group_id: Annotated[Union[int, str], Field(description="Group ID for the IP destination group.")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Get a specific ZIA IP destination group by ID."""
    if not group_id:
        raise ValueError("group_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall
    
    group, _, err = zia.get_ip_destination_group(group_id)
    if err:
        raise Exception(f"Failed to retrieve IP destination group {group_id}: {err}")
    return group.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zia_create_ip_destination_group(
    name: Annotated[str, Field(description="Name of the destination group (required).")],
    type: Annotated[str, Field(description="Group type: DSTN_IP, DSTN_FQDN, DSTN_DOMAIN, or DSTN_OTHER (required).")],
    description: Annotated[Optional[str], Field(description="Description of the group.")] = None,
    addresses: Annotated[Optional[Union[List[str], str]], Field(description="List of IPs/FQDNs. Required for DSTN_IP or DSTN_FQDN types.")] = None,
    countries: Annotated[Optional[Union[List[str], str]], Field(description="List of country codes (e.g., COUNTRY_CA). Optional for DSTN_OTHER.")] = None,
    ip_categories: Annotated[Optional[Union[List[str], str]], Field(description="List of URL categories. Optional for DSTN_OTHER.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Create a new ZIA IP destination group."""
    if not name or not type:
        raise ValueError("name and type are required")
    
    # Normalize list fields
    addresses = _parse_list(addresses)
    countries = _parse_list(countries)
    ip_categories = _parse_list(ip_categories)
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall
    
    group, _, err = zia.add_ip_destination_group(
        name=name,
        description=description,
        type=type,
        addresses=addresses,
        countries=countries,
        ip_categories=ip_categories,
    )
    if err:
        raise Exception(f"Failed to add IP destination group: {err}")
    return group.as_dict()


def zia_update_ip_destination_group(
    group_id: Annotated[Union[int, str], Field(description="Group ID (required).")],
    name: Annotated[str, Field(description="Name of the destination group (required).")],
    type: Annotated[str, Field(description="Group type: DSTN_IP, DSTN_FQDN, DSTN_DOMAIN, or DSTN_OTHER (required).")],
    description: Annotated[Optional[str], Field(description="Description of the group.")] = None,
    addresses: Annotated[Optional[Union[List[str], str]], Field(description="List of IPs/FQDNs.")] = None,
    countries: Annotated[Optional[Union[List[str], str]], Field(description="List of country codes.")] = None,
    ip_categories: Annotated[Optional[Union[List[str], str]], Field(description="List of URL categories.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Update an existing ZIA IP destination group."""
    if not group_id or not name or not type:
        raise ValueError("group_id, name, and type are required for update")
    
    # Normalize list fields
    addresses = _parse_list(addresses)
    countries = _parse_list(countries)
    ip_categories = _parse_list(ip_categories)
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall
    
    group, _, err = zia.update_ip_destination_group(
        group_id=group_id,
        name=name,
        description=description,
        type=type,
        addresses=addresses,
        countries=countries,
        ip_categories=ip_categories,
    )
    if err:
        raise Exception(f"Failed to update IP destination group {group_id}: {err}")
    return group.as_dict()


def zia_delete_ip_destination_group(
    group_id: Annotated[Union[int, str], Field(description="Group ID (required).")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}"
) -> str:
    """Delete a ZIA IP destination group."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zia_delete_ip_destination_group",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not group_id:
        raise ValueError("group_id is required for delete")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall
    
    _, _, err = zia.delete_ip_destination_group(group_id)
    if err:
        raise Exception(f"Failed to delete IP destination group {group_id}: {err}")
    return f"Group {group_id} deleted successfully"
