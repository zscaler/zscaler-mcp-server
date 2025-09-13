from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zdx_device_discovery_tool(
    action: Annotated[
        Literal["list_devices", "read_device"],
        Field(description="Must be one of 'list_devices' or 'read_device'."),
    ],
    device_id: Annotated[
        Optional[str], Field(description="Required if action is 'read_device'.")
    ] = None,
    emails: Annotated[
        Optional[List[str]], Field(description="Filter by email addresses.")
    ] = None,
    user_ids: Annotated[
        Optional[List[str]], Field(description="Filter by user IDs.")
    ] = None,
    mac_address: Annotated[
        Optional[str], Field(description="Filter by MAC address.")
    ] = None,
    private_ipv4: Annotated[
        Optional[str], Field(description="Filter by private IPv4 address.")
    ] = None,
    location_id: Annotated[
        Optional[List[str]], Field(description="Filter by location ID(s).")
    ] = None,
    department_id: Annotated[
        Optional[List[str]], Field(description="Filter by department ID(s).")
    ] = None,
    geo_id: Annotated[
        Optional[List[str]], Field(description="Filter by geolocation ID(s).")
    ] = None,
    since: Annotated[
        Optional[int], Field(description="Number of hours to look back (default 2h).")
    ] = None,
    offset: Annotated[
        Optional[str], Field(description="Offset string for pagination (next_offset).")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> Union[Dict[str, Any], List[Dict[str, Any]], str]:
    """
    Tool for discovering ZDX devices using various filters.

    Supports both:
    - list_devices: Returns a list of active ZDX devices matching the query.
    - read_device: Returns a single device record by device_id.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

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

    if action == "read_device":
        if not device_id:
            raise ValueError("device_id is required for action=read_device")
        result, _, err = client.zdx.devices.get_device(
            device_id, query_params=query_params
        )
        if err:
            raise Exception(f"Device lookup failed: {err}")
        
        # The ZDX SDK returns a list containing a single DeviceDetail object
        if result and len(result) > 0:
            device_obj = result[0]  # Get the first (and only) DeviceDetail object
            return device_obj.as_dict()
        else:
            return {}

    elif action == "list_devices":
        results, _, err = client.zdx.devices.list_devices(query_params=query_params)
        if err:
            raise Exception(f"Device listing failed: {err}")
        
        # The ZDX SDK returns a list containing a single Devices object
        # The Devices object contains a list of DeviceDetail objects in its devices property
        if results and len(results) > 0:
            devices_obj = results[0]  # Get the first (and only) Devices object
            # Access the devices property which contains a list of DeviceDetail objects
            device_list = devices_obj.devices if hasattr(devices_obj, 'devices') else []
            return [d.as_dict() for d in device_list]
        else:
            return []

    else:
        raise ValueError("Invalid action. Must be one of: 'list_devices', 'read_device'")
