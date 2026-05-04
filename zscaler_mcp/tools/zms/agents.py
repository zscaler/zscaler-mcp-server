"""
ZMS Agents Tools

Provides read-only tools for listing and inspecting Zscaler Microsegmentation agents.
"""

import os
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.tools.zms import apply_jmespath_query


def zms_list_agents(
    page: Annotated[
        int,
        Field(description="Page number (default 1)."),
    ] = 1,
    page_size: Annotated[
        int,
        Field(description="Number of items per page (default 20, max 100)."),
    ] = 20,
    search: Annotated[
        Optional[str],
        Field(description="Search filter string to narrow agents by name, IP, etc."),
    ] = None,
    sort: Annotated[
        Optional[str],
        Field(description="Sort field (e.g., 'name', 'connectionStatus')."),
    ] = None,
    sort_dir: Annotated[
        Optional[str],
        Field(description="Sort direction: ASC or DESC."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection on the result. Example: \"nodes[?connection_status=='CONNECTED']\"."),
    ] = None,
    service: Annotated[
        Optional[str],
        Field(description="The service to use."),
    ] = None,
) -> List[Dict[str, Any]]:
    """
    List Zscaler Microsegmentation (ZMS) agents with pagination and search.

    Returns agents with connection status, OS info, version, IP addresses,
    and agent group membership. Supports JMESPath client-side filtering via the query parameter.

    Use this tool to:
    - View all deployed microsegmentation agents
    - Check agent connection status across your environment
    - Search for specific agents by name or IP
    - Monitor agent software versions
    - Use JMESPath queries for advanced filtering (e.g., nodes[?connection_status=='CONNECTED'])
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(service="zms")

    kwargs: Dict[str, Any] = {
        "customer_id": customer_id,
        "page": page,
        "page_size": page_size,
    }
    if search is not None:
        kwargs["search"] = search
    if sort is not None:
        kwargs["sort"] = sort
    if sort_dir is not None:
        kwargs["sort_dir"] = sort_dir

    result, response, err = client.zms.agents.list_agents(**kwargs)

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No agents found."}]
    return apply_jmespath_query(result, query)


def zms_get_agent_connection_status_statistics(
    search: Annotated[
        Optional[str],
        Field(description="Optional search filter."),
    ] = None,
    service: Annotated[
        Optional[str],
        Field(description="The service to use."),
    ] = None,
) -> List[Dict[str, Any]]:
    """
    Get aggregated connection status statistics for ZMS agents.

    Returns total agent count, percentage breakdown, and per-type/status counts.

    Use this tool to:
    - Get an overview of how many agents are connected vs disconnected
    - Monitor agent fleet health
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(service="zms")

    kwargs: Dict[str, Any] = {"customer_id": customer_id}
    if search is not None:
        kwargs["search"] = search

    result, response, err = client.zms.agents.get_agent_connection_status_statistics(**kwargs)

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No agent connection statistics found."}]
    return [result]


def zms_get_agent_version_statistics(
    search: Annotated[
        Optional[str],
        Field(description="Optional search filter."),
    ] = None,
    service: Annotated[
        Optional[str],
        Field(description="The service to use."),
    ] = None,
) -> List[Dict[str, Any]]:
    """
    Get aggregated version statistics for ZMS agents.

    Returns the distribution of agent software versions across your fleet.

    Use this tool to:
    - Identify agents running outdated versions
    - Track upgrade rollout progress
    - Verify version consistency across the fleet
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(service="zms")

    kwargs: Dict[str, Any] = {"customer_id": customer_id}
    if search is not None:
        kwargs["search"] = search

    result, response, err = client.zms.agents.get_agent_version_statistics(**kwargs)

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No agent version statistics found."}]
    return [result]
