from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def zpa_list_ba_certificates(
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    query_params: Annotated[Optional[Dict], Field(description="Optional query parameters for filtering.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> List[Dict]:
    """List ZPA Browser Access (BA) certificates."""
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.certificates
    
    qp = query_params or {}
    if microtenant_id:
        qp["microtenant_id"] = microtenant_id
    
    certs, _, err = api.list_issued_certificates(query_params=qp)
    if err:
        raise Exception(f"Failed to list BA certificates: {err}")
    return [c.as_dict() for c in certs]


def zpa_get_ba_certificate(
    certificate_id: Annotated[str, Field(description="Certificate ID for the BA certificate.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    query_params: Annotated[Optional[Dict], Field(description="Optional query parameters.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Get a specific ZPA Browser Access certificate by ID."""
    if not certificate_id:
        raise ValueError("certificate_id is required")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.certificates
    
    qp = query_params or {}
    if microtenant_id:
        qp["microtenant_id"] = microtenant_id
    
    cert, _, err = api.get_certificate(certificate_id, query_params=qp)
    if err:
        raise Exception(f"Failed to get BA certificate {certificate_id}: {err}")
    return cert.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def zpa_create_ba_certificate(
    name: Annotated[str, Field(description="Name of the certificate.")],
    cert_blob: Annotated[str, Field(description="Required PEM string for the certificate.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Create a new ZPA Browser Access certificate."""
    if not name or not cert_blob:
        raise ValueError("Both name and cert_blob are required for certificate creation")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.certificates
    
    body = {"name": name, "cert_blob": cert_blob}
    if microtenant_id:
        body["microtenant_id"] = microtenant_id
    
    created, _, err = api.add_certificate(**body)
    if err:
        raise Exception(f"Failed to create BA certificate: {err}")
    return created.as_dict()


def zpa_delete_ba_certificate(
    certificate_id: Annotated[str, Field(description="Certificate ID for the BA certificate.")],
    microtenant_id: Annotated[Optional[str], Field(description="Microtenant ID for scoping.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}"
) -> str:
    """Delete a ZPA Browser Access certificate."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zpa_delete_ba_certificate",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check
    

    if not certificate_id:
        raise ValueError("certificate_id is required for deletion")
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.certificates
    
    _, _, err = api.delete_certificate(certificate_id, microtenant_id=microtenant_id)
    if err:
        raise Exception(f"Failed to delete BA certificate {certificate_id}: {err}")
    return f"Successfully deleted BA certificate {certificate_id}"
