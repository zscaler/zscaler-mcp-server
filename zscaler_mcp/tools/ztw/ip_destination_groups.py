import json
from typing import Annotated, Dict, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.utils.utils import validate_and_convert_country_codes


def _parse_list(val):
    """Helper to parse JSON string to list."""
    if isinstance(val, str):
        return json.loads(val)
    return val


# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def ztw_list_ip_destination_groups(
    exclude_type: Annotated[Optional[str], Field(description="Optional filter to exclude groups of type DSTN_IP, DSTN_FQDN, etc.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
) -> List[Dict]:
    """List ZTW IP destination groups with optional filtering."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    ztw = client.ztw.ip_destination_groups
    
    query_params = {"exclude_type": exclude_type} if exclude_type else {}
    groups, _, err = ztw.list_ip_destination_groups(query_params=query_params)
    if err:
        raise Exception(f"Failed to list IP destination groups: {err}")
    return [g.as_dict() for g in groups]


def ztw_list_ip_destination_groups_lite(
    exclude_type: Annotated[Optional[str], Field(description="Optional filter to exclude groups of type DSTN_IP, DSTN_FQDN, etc.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
) -> List[Dict]:
    """List ZTW IP destination groups (lightweight version) with optional filtering."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    ztw = client.ztw.ip_destination_groups
    
    query_params = {"exclude_type": exclude_type} if exclude_type else {}
    groups, _, err = ztw.list_ip_destination_groups_lite(query_params=query_params)
    if err:
        raise Exception(f"Failed to list IP destination groups (lite): {err}")
    return [g.as_dict() for g in groups]


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def ztw_create_ip_destination_group(
    name: Annotated[str, Field(description="Name of the destination group (required).")],
    type: Annotated[str, Field(description="Group type: DSTN_IP, DSTN_FQDN, DSTN_DOMAIN, or DSTN_OTHER (required).")],
    description: Annotated[Optional[str], Field(description="Description of the group.")] = None,
    addresses: Annotated[Optional[Union[List[str], str]], Field(description="List of IPs/FQDNs. Required for DSTN_IP or DSTN_FQDN types.")] = None,
    countries: Annotated[Optional[Union[List[str], str]], Field(description="List of countries (e.g., 'Canada', 'US', 'CA'). Will be converted to COUNTRY_XX format. Only for DSTN_OTHER.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
) -> Dict:
    """Create a new ZTW IP destination group."""
    if not name or not type:
        raise ValueError("name and type are required")
    
    # Normalize list fields
    addresses = _parse_list(addresses)
    
    # Validate and convert country codes to Zscaler format
    if countries:
        try:
            countries = validate_and_convert_country_codes(countries)
        except ValueError as e:
            raise ValueError(f"Invalid country code: {e}")
        
        # Validate that countries are only used with DSTN_OTHER type
        if type != "DSTN_OTHER":
            raise ValueError("Countries are only supported when type is DSTN_OTHER")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    ztw = client.ztw.ip_destination_groups
    
    group, _, err = ztw.add_ip_destination_group(
        name=name,
        description=description,
        type=type,
        addresses=addresses,
        countries=countries,
    )
    if err:
        raise Exception(f"Failed to add IP destination group: {err}")
    return group.as_dict()


def ztw_delete_ip_destination_group(
    group_id: Annotated[Union[int, str], Field(description="Group ID (required).")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
    kwargs: str = "{}"
) -> str:
    """Delete a ZTW IP destination group.
    
    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "ztw_delete_ip_destination_group",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not group_id:
        raise ValueError("group_id is required for delete")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    ztw = client.ztw.ip_destination_groups
    
    _, _, err = ztw.delete_ip_destination_group(group_id)
    if err:
        raise Exception(f"Failed to delete IP destination group {group_id}: {err}")
    return f"Group {group_id} deleted successfully"
