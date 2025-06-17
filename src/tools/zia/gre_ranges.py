from src.sdk.zscaler_client import get_zscaler_client
from typing import Union

def gre_range_discovery_manager(
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    username: str,
    password: str,
    api_key: str,
    use_legacy: bool = False,
    service: str = "zia",
    internal_ip_range: str = None,
    static_ip: str = None,
    limit: int = None,
) -> Union[list[dict], str]:
    """
    Tool for discovering available GRE internal IP ranges in ZIA.

    This tool invokes the list_gre_ranges() function to return available GRE ranges.

    Optional filters:
    - internal_ip_range (str): CIDR range (e.g., '172.17.47.247-172.17.47.240')
    - static_ip (str): Filter by the associated static IP address
    - limit (int): Max number of ranges to return

    If no filters are provided, returns all available ranges from the upstream API.
    """
    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
        username=username,
        password=password,
        api_key=api_key,
        use_legacy=use_legacy,
        service=service,
    )

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
