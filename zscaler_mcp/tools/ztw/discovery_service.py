from typing import Annotated, Dict

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def ztw_get_discovery_settings(
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
) -> Dict:
    """
    Retrieves the workload discovery service settings from Zscaler Cloud & Branch Connector (ZTW).
    This is a read-only operation.

    The workload discovery service settings control how Zscaler discovers and manages workloads
    in your cloud infrastructure. These settings include configuration for discovery roles,
    external IDs, and other discovery-related parameters.

    Args:
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "ztw").

    Returns:
        dict: The discovery service settings object containing:
            - Configuration for workload discovery
            - Discovery role settings
            - External ID settings
            - Other discovery-related parameters

    Raises:
        Exception: If the discovery settings retrieval fails.

    Example:
        Get the current discovery service settings:
        >>> settings = ztw_get_discovery_settings()
        >>> print(f"Discovery settings: {settings}")

        Get discovery settings using legacy API:
        >>> settings = ztw_get_discovery_settings(use_legacy=True)
        >>> print(f"Discovery role: {settings.get('discovery_role', 'N/A')}")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.ztw.discovery_service

    settings, _, err = api.get_discovery_settings()
    if err:
        raise Exception(f"Failed to get ZTW discovery settings: {err}")

    return settings.as_dict()
