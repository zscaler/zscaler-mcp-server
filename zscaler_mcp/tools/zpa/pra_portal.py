from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zpa_list_pra_portals(
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    query_params: Annotated[Optional[Dict], Field(description="Optional query parameters for filtering.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> List[Dict]:
    """List ZPA PRA (Privileged Remote Access) portals."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.pra_portal
    
    qp = query_params or {}
    if microtenant_id:
        qp["microtenant_id"] = microtenant_id
    
    portals, _, err = api.list_portals(query_params=qp)
    if err:
        raise Exception(f"Failed to list PRA portals: {err}")
    return [p.as_dict() for p in portals]


def zpa_get_pra_portal(
    portal_id: Annotated[str, Field(description="Portal ID for the PRA portal.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Get a specific ZPA PRA portal by ID."""
    if not portal_id:
        raise ValueError("portal_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.pra_portal
    
    result, _, err = api.get_portal(portal_id, query_params={"microtenant_id": microtenant_id})
    if err:
        raise Exception(f"Failed to get PRA portal {portal_id}: {err}")
    return result.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zpa_create_pra_portal(
    name: Annotated[str, Field(description="Name of the PRA portal.")],
    domain: Annotated[str, Field(description="Domain for the portal.")],
    certificate_id: Annotated[Optional[str], Field(description="Certificate ID (will auto-resolve from name if not provided).")] = None,
    description: Annotated[Optional[str], Field(description="Description of the PRA portal.")] = None,
    enabled: Annotated[bool, Field(description="Whether the portal is enabled.")] = True,
    user_notification: Annotated[Optional[str], Field(description="User notification message for the portal.")] = None,
    user_notification_enabled: Annotated[Optional[bool], Field(description="Whether user notifications are enabled.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Create a new ZPA PRA portal."""
    if not all([name, domain]):
        raise ValueError("Both 'name' and 'domain' are required for portal creation")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.pra_portal
    
    # Attempt to resolve certificate ID by name if not directly provided
    if not certificate_id:
        certs, _, err = client.zpa.certificates.list_issued_certificates(query_params={"search": name})
        if err:
            raise Exception(f"Failed to resolve certificate: {err}")
        if not certs:
            raise ValueError(f"No certificate found matching name: {name}. Please provide certificate_id explicitly.")
        certificate_id = certs[0].id
    
    payload = {
        "name": name,
        "description": description,
        "enabled": enabled,
        "domain": domain,
        "certificate_id": certificate_id,
        "user_notification": user_notification,
        "user_notification_enabled": user_notification_enabled,
    }
    if microtenant_id:
        payload["microtenant_id"] = microtenant_id
    
    created, _, err = api.add_portal(**payload)
    if err:
        raise Exception(f"Failed to create PRA portal: {err}")
    return created.as_dict()


def zpa_update_pra_portal(
    portal_id: Annotated[str, Field(description="Portal ID for the PRA portal.")],
    name: Annotated[Optional[str], Field(description="Name of the PRA portal.")] = None,
    domain: Annotated[Optional[str], Field(description="Domain for the portal.")] = None,
    certificate_id: Annotated[Optional[str], Field(description="Certificate ID.")] = None,
    description: Annotated[Optional[str], Field(description="Description of the PRA portal.")] = None,
    enabled: Annotated[Optional[bool], Field(description="Whether the portal is enabled.")] = None,
    user_notification: Annotated[Optional[str], Field(description="User notification message for the portal.")] = None,
    user_notification_enabled: Annotated[Optional[bool], Field(description="Whether user notifications are enabled.")] = None,
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Update an existing ZPA PRA portal."""
    if not portal_id:
        raise ValueError("portal_id is required for update")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.pra_portal
    
    update_fields = {
        "name": name,
        "description": description,
        "enabled": enabled,
        "domain": domain,
        "certificate_id": certificate_id,
        "user_notification": user_notification,
        "user_notification_enabled": user_notification_enabled,
    }
    if microtenant_id:
        update_fields["microtenant_id"] = microtenant_id
    
    updated, _, err = api.update_portal(portal_id, **update_fields)
    if err:
        raise Exception(f"Failed to update PRA portal {portal_id}: {err}")
    return updated.as_dict()


def zpa_delete_pra_portal(
    portal_id: Annotated[str, Field(description="Portal ID for the PRA portal.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}"
) -> str:
    """Delete a ZPA PRA portal."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zpa_delete_pra_portal",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not portal_id:
        raise ValueError("portal_id is required for delete")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.pra_portal
    
    _, _, err = api.delete_portal(portal_id, microtenant_id=microtenant_id)
    if err:
        raise Exception(f"Failed to delete PRA portal {portal_id}: {err}")
    return f"Successfully deleted PRA portal {portal_id}"
