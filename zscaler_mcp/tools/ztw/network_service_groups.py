from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================

def ztw_list_network_service_groups(
    search: Annotated[Optional[str], Field(description="Optional search string for filtering results by group name or description.")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
) -> List[Dict]:
    """
    List ZTW network service groups with optional search filtering.
    
    This provides read-only access to network service groups. Network service groups
    are collections of network services that can be used for policy configuration and
    traffic management in Zscaler Trusted Web.
    
    Note: This is a read-only operation. Network service groups cannot be created,
    updated, or deleted through this tool.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    ztw = client.ztw.nw_service_groups
    
    query_params = {"search": search} if search else {}
    groups, _, err = ztw.list_network_svc_groups(query_params=query_params)
    if err:
        raise Exception(f"Error listing network service groups: {err}")
    return [g.as_dict() for g in groups]
