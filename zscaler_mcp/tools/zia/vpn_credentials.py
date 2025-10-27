from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zia_list_vpn_credentials(
    query_params: Annotated[Optional[Dict], Field(description="Optional query parameters for filtering.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict]:
    """List ZIA VPN credentials."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.traffic_vpn_credentials
    
    credentials, _, err = api.list_vpn_credentials(query_params=query_params)
    if err:
        raise Exception(f"List failed: {err}")
    return [c.as_dict() for c in credentials]


def zia_get_vpn_credential(
    credential_id: Annotated[int, Field(description="Credential ID.")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Get a specific ZIA VPN credential by ID."""
    if not credential_id:
        raise ValueError("credential_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.traffic_vpn_credentials
    
    result, _, err = api.get_vpn_credential(credential_id)
    if err:
        raise Exception(f"Read failed: {err}")
    return result.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zia_create_vpn_credential(
    credential_type: Annotated[str, Field(description="Type of credential: 'IP' or 'UFQDN' (required).")],
    pre_shared_key: Annotated[str, Field(description="Pre-shared key (required).")],
    ip_address: Annotated[Optional[str], Field(description="IP address (required for type 'IP').")] = None,
    fqdn: Annotated[Optional[str], Field(description="FQDN (required for type 'UFQDN').")] = None,
    comments: Annotated[Optional[str], Field(description="Optional comments for the credential.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Create a new ZIA VPN credential."""
    if credential_type not in ["IP", "UFQDN"]:
        raise ValueError("credential_type must be 'IP' or 'UFQDN'")
    if not pre_shared_key:
        raise ValueError("pre_shared_key is required for VPN credential creation")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.traffic_vpn_credentials
    
    body = {
        "type": credential_type,
        "pre_shared_key": pre_shared_key,
        "comments": comments,
    }
    if credential_type == "IP":
        if not ip_address:
            raise ValueError("ip_address is required for type 'IP'")
        body["ip_address"] = ip_address
    else:
        if not fqdn:
            raise ValueError("fqdn is required for type 'UFQDN'")
        body["fqdn"] = fqdn
    
    created, _, err = api.add_vpn_credential(**body)
    if err:
        raise Exception(f"Create failed: {err}")
    return created.as_dict()


def zia_update_vpn_credential(
    credential_id: Annotated[int, Field(description="Credential ID (required).")],
    pre_shared_key: Annotated[Optional[str], Field(description="Pre-shared key.")] = None,
    comments: Annotated[Optional[str], Field(description="Optional comments for the credential.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Update an existing ZIA VPN credential. Note: fqdn/ip_address cannot be changed."""
    if not credential_id:
        raise ValueError("credential_id is required for update")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.traffic_vpn_credentials
    
    update_fields = {
        "pre_shared_key": pre_shared_key,
        "comments": comments,
    }
    updated, _, err = api.update_vpn_credential(credential_id, **update_fields)
    if err:
        raise Exception(f"Update failed: {err}")
    return updated.as_dict()


def zia_delete_vpn_credential(
    credential_id: Annotated[int, Field(description="Credential ID (required).")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}"
) -> str:
    """Delete a ZIA VPN credential."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zia_delete_vpn_credential",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not credential_id:
        raise ValueError("credential_id is required for deletion")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zia.traffic_vpn_credentials
    
    _, _, err = api.delete_vpn_credential(credential_id)
    if err:
        raise Exception(f"Delete failed: {err}")
    return f"Deleted VPN credential {credential_id}"
