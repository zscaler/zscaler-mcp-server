from typing import Annotated, Any, Dict

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# ============================================================================
# READ-ONLY OPERATIONS
# ============================================================================


def zeasm_list_organizations(
    service: Annotated[str, Field(description="The service to use.")] = "zeasm",
) -> Dict[str, Any]:
    """
    List all organizations configured for a tenant in the ZEASM Admin Portal.
    
    This is a read-only operation that retrieves all organizations configured
    for external attack surface management.
    
    Args:
        service (str): The service to use (default: "zeasm").
    
    Returns:
        dict: Dictionary containing:
            - results: List of organization objects
            - total_results: Total number of organizations
    
    Example:
        List all organizations:
        >>> orgs = zeasm_list_organizations()
        >>> print(f"Total: {orgs['total_results']}")
        >>> for org in orgs['results']:
        ...     print(f"  {org['id']}: {org['name']}")
    """
    client = get_zscaler_client(use_legacy=False, service=service)
    
    orgs, _, err = client.zeasm.organizations.list_organizations()
    if err:
        raise Exception(f"Failed to list EASM organizations: {err}")
    
    return orgs.as_dict()
