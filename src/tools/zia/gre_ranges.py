from src.sdk.zscaler_client import get_zscaler_client
from src.zscaler_mcp import app
from typing import Annotated, Union, List
from pydantic import Field


@app.tool(
    name="zia_gre_range",
    description="Tool for discovering available GRE internal IP ranges in ZIA.",
)
def gre_range_discovery_manager(
    internal_ip_range: Annotated[
        str,
        Field(description="CIDR range (e.g., '172.17.47.247-172.17.47.240')")
    ] = None,
    static_ip: Annotated[
        str,
        Field(description="Filter by the associated static IP address")
    ] = None,
    limit: Annotated[
        int,
        Field(description="Max number of ranges to return")
    ] = None,
    use_legacy: Annotated[
        bool,
        Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[
        str,
        Field(description="The service to use.")
    ] = "zia",
) -> Union[List[dict], str]:
    """
    Tool for discovering available GRE internal IP ranges in ZIA.

    This tool invokes the list_gre_ranges() function to return available GRE ranges.

    Optional filters:
    - internal_ip_range (str): CIDR range (e.g., '172.17.47.247-172.17.47.240')
    - static_ip (str): Filter by the associated static IP address
    - limit (int): Max number of ranges to return

    If no filters are provided, returns all available ranges from the upstream API.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    gre_api = client.zia.gre_tunnel

    query_params = {}
    if internal_ip_range:
        query_params["internal_ip_range"] = internal_ip_range
    if static_ip:
        query_params["static_ip"] = static_ip
    if limit:
        query_params["limit"] = limit

    ranges, _, err = gre_api.list_gre_ranges(query_params=query_params if query_params else None)
    if err:
        raise Exception(f"Failed to retrieve GRE ranges: {err}")

    return ranges
