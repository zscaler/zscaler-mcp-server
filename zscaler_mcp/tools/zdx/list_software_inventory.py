from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# ============================================================================
# READ-ONLY OPERATIONS
# ============================================================================

def zdx_list_software(
    location_id: Annotated[
        Optional[List[str]], Field(description="Filter by location ID(s).")
    ] = None,
    department_id: Annotated[
        Optional[List[str]], Field(description="Filter by department ID(s).")
    ] = None,
    geo_id: Annotated[
        Optional[List[str]], Field(description="Filter by geolocation ID(s).")
    ] = None,
    user_ids: Annotated[
        Optional[List[str]], Field(description="Filter by user ID(s).")
    ] = None,
    device_ids: Annotated[
        Optional[List[str]], Field(description="Filter by device ID(s).")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> List[Dict[str, Any]]:
    """
    Lists all software in the ZDX inventory with optional filtering.
    This is a read-only operation.

    Returns a list of all software in ZDX with optional filtering by location,
    department, geolocation, users, or devices. Use this for getting an overview
    of all software in the organization. The response provides software keys that
    can be used to get detailed information about specific software.

    Args:
        location_id: Optional list of location IDs to filter by specific locations.
        department_id: Optional list of department IDs to filter by specific departments.
        geo_id: Optional list of geolocation IDs to filter by geographic regions.
        user_ids: Optional list of user IDs to filter by specific users.
        device_ids: Optional list of device IDs to filter by specific devices.
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        List of dictionaries containing software inventory information.

    Raises:
        Exception: If the software inventory retrieval fails due to API errors.

    Examples:
        Get overview of all software:
        >>> software = zdx_list_software()

        Get software for specific users:
        >>> user_software = zdx_list_software(user_ids=["12345", "67890"])

        Get software for specific devices:
        >>> device_software = zdx_list_software(device_ids=["device1", "device2"])
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    query_params = {}
    if location_id:
        query_params["location_id"] = location_id
    if department_id:
        query_params["department_id"] = department_id
    if geo_id:
        query_params["geo_id"] = geo_id
    if user_ids:
        query_params["user_ids"] = user_ids
    if device_ids:
        query_params["device_ids"] = device_ids

    result, _, err = client.zdx.inventory.list_software(query_params=query_params)
    if err:
        raise Exception(f"Software inventory listing failed: {err}")

    if result and len(result) > 0:
        inventory_obj = result[0]
        software_list = inventory_obj.software if hasattr(inventory_obj, 'software') else []
        return [software.as_dict() for software in software_list]
    else:
        return []


def zdx_get_software_details(
    software_key: Annotated[
        str, Field(description="The software name and version key.")
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
    user_ids: Annotated[
        Optional[List[str]], Field(description="Filter by user ID(s).")
    ] = None,
    device_ids: Annotated[
        Optional[List[str]], Field(description="Filter by device ID(s).")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> List[Dict[str, Any]]:
    """
    Gets detailed information about a specific software including all users and devices.
    This is a read-only operation.

    Returns a list of all users and devices for a given software name and version.
    Use this only when you need detailed information about a particular software key.
    The software keys are obtained from the zdx_list_software operation.

    Args:
        software_key: The software name and version key (required).
        location_id: Optional list of location IDs to filter by specific locations.
        department_id: Optional list of department IDs to filter by specific departments.
        geo_id: Optional list of geolocation IDs to filter by geographic regions.
        user_ids: Optional list of user IDs to filter by specific users.
        device_ids: Optional list of device IDs to filter by specific devices.
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        List of dictionaries containing users and devices for the specified software.

    Raises:
        Exception: If the software details retrieval fails due to API errors.

    Examples:
        Get details for specific software:
        >>> details = zdx_get_software_details(software_key="Chrome_120.0.6099.109")

        Get details with location filter:
        >>> details = zdx_get_software_details(
        ...     software_key="Chrome_120.0.6099.109",
        ...     location_id=["58755"]
        ... )
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    query_params = {}
    if location_id:
        query_params["location_id"] = location_id
    if department_id:
        query_params["department_id"] = department_id
    if geo_id:
        query_params["geo_id"] = geo_id
    if user_ids:
        query_params["user_ids"] = user_ids
    if device_ids:
        query_params["device_ids"] = device_ids

    result, _, err = client.zdx.inventory.get_software(software_key, query_params=query_params)
    if err:
        raise Exception(f"Software details lookup failed: {err}")

    if result and len(result) > 0:
        software_obj = result[0]
        devices_list = software_obj.devices if hasattr(software_obj, 'devices') else []
        return [device.as_dict() for device in devices_list]
    else:
        return []
