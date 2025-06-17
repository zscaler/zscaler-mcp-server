from src.sdk.zscaler_client import get_zscaler_client
from typing import Union, List, Dict, Any


def zdx_device_discovery_tool(
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    key_id: str,
    key_secret: str,
    action: str,
    device_id: str = None,
    emails: List[str] = None,
    user_ids: List[str] = None,
    mac_address: str = None,
    private_ipv4: str = None,
    location_id: List[str] = None,
    department_id: List[str] = None,
    geo_id: List[str] = None,
    since: int = None,
    offset: str = None,
    use_legacy: bool = False,
    service: str = "zdx",
) -> Union[Dict[str, Any], List[Dict[str, Any]], str]:
    """
    Tool for discovering ZDX devices using various filters.

    Supports both:
    - list_devices: Returns a list of active ZDX devices matching the query.
    - get_device: Returns a single device record by device_id.

    Args:
        action (str): Must be one of "list_devices" or "get_device".
        device_id (str, optional): Required if action is "get_device".
        emails (List[str], optional): Filter by email addresses.
        user_ids (List[str], optional): Filter by user IDs.
        mac_address (str, optional): Filter by MAC address.
        private_ipv4 (str, optional): Filter by private IPv4.
        location_id (List[str], optional): Filter by location ID(s).
        department_id (List[str], optional): Filter by department ID(s).
        geo_id (List[str], optional): Filter by geolocation ID(s).
        since (int, optional): Number of hours to look back (default 2h).
        offset (str, optional): Offset string for pagination (next_offset).

    Returns:
        Union[dict, list[dict], str]: Device record(s) from ZDX.

    Examples:
        >>> zdx_device_discovery_tool(..., action="get_device", device_id="12345678")
        >>> zdx_device_discovery_tool(..., action="list_devices", emails=["jdoe@example.com"], since=24)
    """
    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
        key_id=key_id,
        key_secret=key_secret,
        use_legacy=use_legacy,
        service=service,
    )

    query_params = {}
    if emails:
        query_params["emails"] = emails
    if user_ids:
        query_params["user_ids"] = user_ids
    if mac_address:
        query_params["mac_address"] = mac_address
    if private_ipv4:
        query_params["private_ipv4"] = private_ipv4
    if location_id:
        query_params["location_id"] = location_id
    if department_id:
        query_params["department_id"] = department_id
    if geo_id:
        query_params["geo_id"] = geo_id
    if since:
        query_params["since"] = since
    if offset:
        query_params["offset"] = offset

    if action == "get_device":
        if not device_id:
            raise ValueError("device_id is required for action=get_device")
        result, _, err = client.zdx.devices.get_device(device_id, query_params=query_params)
        if err:
            raise Exception(f"Device lookup failed: {err}")
        return [d.as_dict() for d in result]

    elif action == "list_devices":
        results, _, err = client.zdx.devices.list_devices(query_params=query_params)
        if err:
            raise Exception(f"Device listing failed: {err}")
        return [r.as_dict() for r in results]

    else:
        raise ValueError("Invalid action. Must be one of: 'list_devices', 'get_device'")
