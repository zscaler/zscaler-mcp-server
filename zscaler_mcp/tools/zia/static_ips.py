from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zia_list_static_ips(
    query_params: Annotated[Optional[Dict], Field(description="Optional query parameters for filtering.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict]:
    """List ZIA static IP addresses."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.traffic_static_ip
    
    results, _, err = api.list_static_ips(query_params=query_params)
    if err:
        raise Exception(f"List failed: {err}")
    return [r.as_dict() for r in results]


def zia_get_static_ip(
    static_ip_id: Annotated[int, Field(description="Static IP ID.")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Get a specific ZIA static IP by ID."""
    if not static_ip_id:
        raise ValueError("static_ip_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.traffic_static_ip
    
    result, _, err = api.get_static_ip(static_ip_id)
    if err:
        raise Exception(f"Read failed: {err}")
    return result.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zia_create_static_ip(
    ip_address: Annotated[str, Field(description="IP address (required).")],
    comment: Annotated[Optional[str], Field(description="Optional comment for the static IP.")] = None,
    geo_override: Annotated[Optional[bool], Field(description="Whether to override geolocation.")] = None,
    routable_ip: Annotated[Optional[bool], Field(description="Whether the IP is routable.")] = None,
    latitude: Annotated[Optional[float], Field(description="Latitude for geolocation override.")] = None,
    longitude: Annotated[Optional[float], Field(description="Longitude for geolocation override.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Create a new ZIA static IP address."""
    if not ip_address:
        raise ValueError("ip_address is required for creating a static IP")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.traffic_static_ip
    
    payload = {
        "ip_address": ip_address,
        "comment": comment,
        "geo_override": geo_override,
        "routable_ip": routable_ip,
        "latitude": latitude,
        "longitude": longitude,
    }
    
    created, _, err = api.add_static_ip(**payload)
    if err:
        raise Exception(f"Create failed: {err}")
    return created.as_dict()


def zia_update_static_ip(
    static_ip_id: Annotated[int, Field(description="Static IP ID (required).")],
    comment: Annotated[Optional[str], Field(description="Optional comment for the static IP.")] = None,
    geo_override: Annotated[Optional[bool], Field(description="Whether to override geolocation.")] = None,
    routable_ip: Annotated[Optional[bool], Field(description="Whether the IP is routable.")] = None,
    latitude: Annotated[Optional[float], Field(description="Latitude for geolocation override.")] = None,
    longitude: Annotated[Optional[float], Field(description="Longitude for geolocation override.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Update an existing ZIA static IP. Note: IP address cannot be changed."""
    if not static_ip_id:
        raise ValueError("static_ip_id is required for update")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.traffic_static_ip
    
    update_data = {
        "comment": comment,
        "geo_override": geo_override,
        "routable_ip": routable_ip,
        "latitude": latitude,
        "longitude": longitude,
    }
    
    updated, _, err = api.update_static_ip(static_ip_id, **update_data)
    if err:
        raise Exception(f"Update failed: {err}")
    return updated.as_dict()


def zia_delete_static_ip(
    static_ip_id: Annotated[int, Field(description="Static IP ID (required).")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}"
) -> str:
    """Delete a ZIA static IP. Note: Must delete associated GRE tunnels first."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zia_delete_static_ip",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not static_ip_id:
        raise ValueError("static_ip_id is required for deletion")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.traffic_static_ip
    
    _, _, err = api.delete_static_ip(static_ip_id)
    if err:
        raise Exception(f"Delete failed: {err}")
    return f"Deleted static IP {static_ip_id}"
