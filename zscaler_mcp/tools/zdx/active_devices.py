from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# ============================================================================
# READ-ONLY OPERATIONS
# ============================================================================

def zdx_list_devices(
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
) -> List[Dict[str, Any]]:
    """
    Lists active ZDX devices using various filters.
    This is a read-only operation.

    Returns a list of active ZDX devices matching the specified query filters.
    Supports filtering by email, user ID, MAC address, IP address, location,
    department, geolocation, and time range.

    Args:
        emails: Optional list of email addresses to filter devices by.
        user_ids: Optional list of user IDs to filter devices by.
        mac_address: Optional MAC address to filter devices by.
        private_ipv4: Optional private IPv4 address to filter devices by.
        location_id: Optional list of location IDs to filter devices by.
        department_id: Optional list of department IDs to filter devices by.
        geo_id: Optional list of geolocation IDs to filter devices by.
        since: Optional number of hours to look back for device data (default 2 hours).
        offset: Optional pagination offset for getting next batch of results.
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        List of device dictionaries containing device information.

    Raises:
        Exception: If the device listing fails due to API errors.

    Examples:
        List all active devices:
        >>> devices = zdx_list_devices()

        List devices for a specific user:
        >>> devices = zdx_list_devices(emails=["user@example.com"])

        List devices by location:
        >>> devices = zdx_list_devices(location_id=["loc123"])
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


def zdx_get_device(
    device_id: Annotated[
        str, Field(description="The unique ID for the ZDX device.")
    ],
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
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> Dict[str, Any]:
    """
    Gets a specific ZDX device by its device ID.
    This is a read-only operation.

    Returns detailed information about a single ZDX device identified by the device_id.

    Args:
        device_id: The unique ID for the ZDX device (required).
        location_id: Optional list of location IDs to filter by.
        department_id: Optional list of department IDs to filter by.
        geo_id: Optional list of geolocation IDs to filter by.
        since: Optional number of hours to look back for device data (default 2 hours).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        Dictionary containing detailed device information.

    Raises:
        Exception: If the device lookup fails due to API errors.

    Examples:
        Get a specific device:
        >>> device = zdx_get_device(device_id="device123")

        Get device with location filter:
        >>> device = zdx_get_device(device_id="device123", location_id=["loc456"])
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    query_params = {}
    if location_id:
        query_params["location_id"] = location_id
    if department_id:
        query_params["department_id"] = department_id
    if geo_id:
        query_params["geo_id"] = geo_id
    if since:
        query_params["since"] = since

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
