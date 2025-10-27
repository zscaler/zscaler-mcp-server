import json
from typing import Annotated, Any, Dict, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zia_list_locations(
    query_params: Annotated[Optional[Dict[str, Any]], Field(description="Optional query parameters for filtering (e.g., search, xff_enabled).")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict[str, Any]]:
    """List all ZIA locations with optional filtering."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    locations_api = client.zia.locations
    
    result, _, err = locations_api.list_locations(query_params=query_params or {})
    if err:
        raise Exception(f"Failed to list locations: {err}")
    return [loc.as_dict() for loc in result or []]


def zia_get_location(
    location_id: Annotated[int, Field(description="Location ID.")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict[str, Any]:
    """Get a specific ZIA location by ID."""
    if not location_id:
        raise ValueError("location_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    locations_api = client.zia.locations
    
    result, _, err = locations_api.get_location(location_id)
    if err:
        raise Exception(f"Failed to get location {location_id}: {err}")
    return result.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zia_create_location(
    location: Annotated[Union[Dict[str, Any], str], Field(description="Location configuration as dictionary or JSON string (required).")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict[str, Any]:
    """
    Create a new ZIA location.
    
    Location Creation Modes:
    1. Static IP-based: Set `ipAddresses` in the payload.
    2. VPN Credential-based: Requires both `ipAddresses` and `vpnCredentials` fields.
    
    Required fields typically include:
    - name (str): Name of the location
    - country (str): Country (e.g., "CANADA")
    - tz (str): Timezone (e.g., "CANADA_AMERICA_VANCOUVER")
    - ipAddresses (list[str]): List of static IPs, CIDRs, or GRE tunnel addresses
    
    Optional fields include:
    - vpnCredentials (list[dict]): Associated VPN credentials with `id` and `type`
    - xffForwardEnabled, authRequired, aupEnabled, ofwEnabled, etc.: Boolean policy flags
    - profile (str): Tag such as "CORPORATE", "SERVER", or "Unassigned"
    - description (str): Optional notes
    """
    if not location:
        raise ValueError("location dictionary or JSON string is required")
    
    if isinstance(location, str):
        try:
            location = json.loads(location)
        except Exception as e:
            raise ValueError(f"Invalid JSON for location: {e}")
    
    if not location.get("ipAddresses") and not location.get("vpnCredentials"):
        raise ValueError(
            "Location creation requires either `ipAddresses` or `vpnCredentials`. "
            "If neither is provided, you may want to create a static IP using the `zia_create_static_ip` tool."
        )
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    locations_api = client.zia.locations
    
    created, _, err = locations_api.add_location(**location)
    if err:
        raise Exception(f"Failed to create location: {err}")
    return created.as_dict()


def zia_update_location(
    location_id: Annotated[int, Field(description="Location ID (required).")],
    location: Annotated[Union[Dict[str, Any], str], Field(description="Updated location configuration as dictionary or JSON string (required).")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict[str, Any]:
    """Update an existing ZIA location."""
    if not location_id or not location:
        raise ValueError("location_id and location configuration are required")
    
    if isinstance(location, str):
        try:
            location = json.loads(location)
        except Exception as e:
            raise ValueError(f"Invalid JSON for location: {e}")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    locations_api = client.zia.locations
    
    updated, _, err = locations_api.update_location(location_id, **location)
    if err:
        raise Exception(f"Failed to update location {location_id}: {err}")
    return updated.as_dict()


def zia_delete_location(
    location_id: Annotated[int, Field(description="Location ID (required).")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}"
) -> str:
    """
    Delete a ZIA location.
    
    Note: Associated resources must be deleted in the reverse order they were created.
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zia_delete_location",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not location_id:
        raise ValueError("location_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    locations_api = client.zia.locations
    
    _, _, err = locations_api.delete_location(location_id)
    if err:
        raise Exception(f"Failed to delete location {location_id}: {err}")
    return f"Deleted location {location_id}"
