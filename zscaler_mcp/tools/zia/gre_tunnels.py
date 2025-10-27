from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zia_list_gre_tunnels(
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict]:
    """List all ZIA GRE tunnels."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    gre_api = client.zia.gre_tunnel
    
    tunnels, _, err = gre_api.list_gre_tunnels()
    if err:
        raise Exception(f"Failed to list GRE tunnels: {err}")
    return [t.as_dict() for t in tunnels]


def zia_get_gre_tunnel(
    tunnel_id: Annotated[int, Field(description="Tunnel ID.")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Get a specific ZIA GRE tunnel by ID."""
    if not tunnel_id:
        raise ValueError("tunnel_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    gre_api = client.zia.gre_tunnel
    
    tunnel, _, err = gre_api.get_gre_tunnel(tunnel_id)
    if err:
        raise Exception(f"Failed to retrieve GRE tunnel {tunnel_id}: {err}")
    return tunnel.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zia_create_gre_tunnel(
    static_ip_address: Annotated[str, Field(description="Static IP address to associate or create (required).")],
    ip_unnumbered: Annotated[Optional[bool], Field(description="If True, tunnel will be unnumbered; if False, a GRE IP range will be selected.")] = None,
    internal_ip_range: Annotated[Optional[str], Field(description="Internal IP range for the GRE tunnel.")] = None,
    comment: Annotated[Optional[str], Field(description="Comment for the GRE tunnel or static IP.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """
    Create a new ZIA GRE tunnel.
    
    This will check for or create a static IP first, then create the GRE tunnel.
    For numbered tunnels (ip_unnumbered=False), the tool will automatically fetch GRE ranges.
    """
    if not static_ip_address:
        raise ValueError("static_ip_address is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    gre_api = client.zia.gre_tunnel
    ip_api = client.zia.traffic_static_ip
    
    # Check or create static IP first
    existing_ips, _, err = ip_api.list_static_ips(query_params={"ip_address": static_ip_address})
    if err:
        raise Exception(f"Failed to search static IP: {err}")
    
    if existing_ips:
        static_ip = existing_ips[0]
    else:
        static_ip, _, err = ip_api.add_static_ip(ip_address=static_ip_address, comment=comment)
        if err:
            raise Exception(f"Failed to create static IP: {err}")
    
    payload = {
        "source_ip": static_ip.ip_address,
        "ip_unnumbered": ip_unnumbered,
        "internal_ip_range": internal_ip_range,
        "comment": comment,
    }
    
    if not ip_unnumbered:
        gre_ranges, _, err = gre_api.list_gre_ranges(query_params={"static_ip": static_ip.ip_address})
        if err:
            raise Exception(f"Failed to fetch GRE ranges: {err}")
        if not gre_ranges or "startIPAddress" not in gre_ranges[0]:
            raise Exception("No valid GRE internal IP ranges found in the response.")
        payload["internal_ip_range"] = gre_ranges[0]["startIPAddress"]
    
    tunnel, _, err = gre_api.add_gre_tunnel(**payload)
    if err:
        raise Exception(f"Failed to create GRE tunnel: {err}")
    return tunnel.as_dict()


def zia_delete_gre_tunnel(
    tunnel_id: Annotated[int, Field(description="Tunnel ID (required).")],
    static_ip_id: Annotated[int, Field(description="Static IP ID to delete after tunnel removal (required).")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}"
) -> str:
    """
    Delete a ZIA GRE tunnel and its associated static IP.
    
    Note: GRE tunnel must be deleted before the static IP.
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zia_delete_gre_tunnel",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not tunnel_id or not static_ip_id:
        raise ValueError("Both tunnel_id and static_ip_id are required for delete")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    gre_api = client.zia.gre_tunnel
    ip_api = client.zia.traffic_static_ip
    
    _, _, err = gre_api.delete_gre_tunnel(tunnel_id)
    if err:
        raise Exception(f"Failed to delete GRE tunnel {tunnel_id}: {err}")
    
    _, _, err = ip_api.delete_static_ip(static_ip_id)
    if err:
        raise Exception(f"Failed to delete static IP {static_ip_id}: {err}")
    
    return f"Deleted GRE tunnel {tunnel_id} and static IP {static_ip_id}"
