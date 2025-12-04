from typing import Annotated, Any, Dict

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# ============================================================================
# READ-ONLY OPERATIONS
# ============================================================================


def zeasm_list_lookalike_domains(
    org_id: Annotated[str, Field(description="The unique identifier for the organization.")],
    service: Annotated[str, Field(description="The service to use.")] = "zeasm",
) -> Dict[str, Any]:
    """
    List all lookalike domains detected for an organization's assets.
    
    This is a read-only operation that retrieves lookalike domains identified by EASM.
    
    Args:
        org_id (str): The unique identifier for the organization.
        service (str): The service to use (default: "zeasm").
    
    Returns:
        dict: Dictionary containing:
            - results: List of lookalike domain objects
            - total_results: Total number of lookalike domains
    
    Example:
        List all lookalike domains for an organization:
        >>> domains = zeasm_list_lookalike_domains(org_id="3f61a446-1a0d-11f0-94e8-8a5f4d45e80c")
        >>> print(f"Total: {domains['total_results']}")
        >>> for domain in domains['results']:
        ...     print(f"  {domain['domain_name']}")
    """
    client = get_zscaler_client(use_legacy=False, service=service)
    
    domains, _, err = client.zeasm.lookalike_domains.list_lookalike_domains(org_id=org_id)
    if err:
        raise Exception(f"Failed to list EASM lookalike domains for organization {org_id}: {err}")
    
    return domains.as_dict()


def zeasm_get_lookalike_domain(
    org_id: Annotated[str, Field(description="The unique identifier for the organization.")],
    lookalike_raw: Annotated[str, Field(description="The lookalike domain name (e.g., 'example-domain.com').")],
    service: Annotated[str, Field(description="The service to use.")] = "zeasm",
) -> Dict[str, Any]:
    """
    Get details for a specific lookalike domain by domain name.
    
    This is a read-only operation that retrieves detailed information about a specific lookalike domain.
    
    Args:
        org_id (str): The unique identifier for the organization.
        lookalike_raw (str): The lookalike domain name (e.g., "assuredartners.com").
        service (str): The service to use (default: "zeasm").
    
    Returns:
        dict: Lookalike domain details object
    
    Example:
        Get details for a specific lookalike domain:
        >>> details = zeasm_get_lookalike_domain(
        ...     org_id="3f61a446-1a0d-11f0-94e8-8a5f4d45e80c",
        ...     lookalike_raw="assuredartners.com"
        ... )
        >>> print(details)
    """
    client = get_zscaler_client(use_legacy=False, service=service)
    
    domain, _, err = client.zeasm.lookalike_domains.get_lookalike_domain(org_id=org_id, lookalike_raw=lookalike_raw)
    if err:
        raise Exception(f"Failed to get EASM lookalike domain details for {lookalike_raw}: {err}")
    
    return domain.as_dict()
