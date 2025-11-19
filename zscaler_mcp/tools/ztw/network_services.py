from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def ztw_list_network_services(
    protocol: Annotated[
        Optional[str],
        Field(
            description="Filter by protocol (e.g., 'ICMP', 'TCP', 'UDP', 'GRE', 'ESP', 'OTHER')."
        ),
    ] = None,
    search: Annotated[
        Optional[str],
        Field(description="Optional search filter applied to the service name or description."),
    ] = None,
    locale: Annotated[
        Optional[str],
        Field(
            description="Optional locale for localized descriptions (e.g., 'en-US', 'de-DE', 'fr-FR')."
        ),
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
) -> List[Dict]:
    """List network services configured in Zscaler Cloud & Branch Connector (ZTW).

    Args:
        protocol: Optional network protocol filter.
        search: Optional search term for service name or description.
        locale: Optional locale code to localize descriptions.
        use_legacy: Whether to use the legacy API (default: False).
        service: The service to use (default: "ztw").

    Returns:
        List[Dict]: A list of network service definitions.

    Raises:
        Exception: If the SDK returns an error response.
    """

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.ztw.nw_service

    query_params: Dict[str, object] = {}
    if protocol:
        query_params["protocol"] = protocol
    if search:
        query_params["search"] = search
    if locale:
        query_params["locale"] = locale

    services, _, err = api.list_network_services(query_params=query_params)
    if err:
        raise Exception(f"Failed to list ZTW network services: {err}")

    return [svc.as_dict() for svc in services]
