from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zdx_list_software_inventory(
    action: Annotated[
        Literal["list_softwares", "list_software_key"],
        Field(description="Must be one of 'list_softwares' or 'list_software_key'."),
    ],
    software_key: Annotated[
        Optional[str], Field(description="Required if action is 'list_software_key'. The software name and version key.")
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
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Tool for retrieving ZDX software inventory information.

    Supports two actions:
    - list_softwares: Returns a list of all software in ZDX with optional filtering (USE THIS FOR GENERAL OVERVIEW).
    - list_software_key: Returns a list of all users and devices for a given software name and version (USE ONLY FOR SPECIFIC SOFTWARE QUERIES).

    USAGE GUIDELINES:
    - Use action='list_softwares' by default to get an overview of all software in the organization
    - Use action='list_software_key' only when the user specifically asks for details about a particular software key
    - The list_softwares action provides software keys that can be used with list_software_key for detailed analysis

    Args:
        action: The type of software inventory information to retrieve ('list_softwares' or 'list_software_key').
        software_key: Required if action is 'list_software_key'. The software name and version key.
        location_id: Optional list of location IDs to filter by specific locations.
        department_id: Optional list of department IDs to filter by specific departments.
        geo_id: Optional list of geolocation IDs to filter by geographic regions.
        user_ids: Optional list of user IDs to filter by specific users.
        device_ids: Optional list of device IDs to filter by specific devices.
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        For 'list_softwares': List of dictionaries containing software inventory information.
        For 'list_software_key': List of dictionaries containing users and devices for the specified software.

    Raises:
        Exception: If the software inventory retrieval fails due to API errors.

    Examples:
        DEFAULT USAGE - Get overview of all software in the organization:
        >>> software_list = zdx_list_software_inventory(action="list_softwares")

        Get software overview for specific users:
        >>> user_software = zdx_list_software_inventory(
        ...     action="list_softwares",
        ...     user_ids=["12345", "67890"]
        ... )

        Get software overview for specific devices:
        >>> device_software = zdx_list_software_inventory(
        ...     action="list_softwares",
        ...     device_ids=["device1", "device2"]
        ... )

        Get software overview for a specific location:
        >>> location_software = zdx_list_software_inventory(
        ...     action="list_softwares",
        ...     location_id=["545845"]
        ... )

        SPECIFIC SOFTWARE QUERY - Get detailed information for a specific software (only when user asks for specific software):
        >>> software_users = zdx_list_software_inventory(
        ...     action="list_software_key",
        ...     software_key="screencaptureui2"
        ... )

        Get specific software details with department filter:
        >>> software_users = zdx_list_software_inventory(
        ...     action="list_software_key",
        ...     software_key="screencaptureui2",
        ...     department_id=["123456"],
        ...     geo_id=["US"]
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

    if action == "list_software_key":
        if not software_key:
            raise ValueError("software_key is required for action=list_software_key")
        result, _, err = client.zdx.inventory.list_software_keys(
            software_key, query_params=query_params
        )
        if err:
            raise Exception(f"Device lookup failed: {err}")

        # The ZDX SDK returns a SoftwareList object
        # The SoftwareList object has a 'software' property containing DeviceSoftwareInventory objects
        if result:
            software_list = []
            # Access the software property which contains DeviceSoftwareInventory objects
            if hasattr(result, 'software') and result.software:
                for software_item in result.software:
                    try:
                        # Convert each DeviceSoftwareInventory object to dictionary
                        if hasattr(software_item, 'as_dict'):
                            software_list.append(software_item.as_dict())
                        else:
                            # Fallback to dict conversion
                            software_list.append(dict(software_item))
                    except Exception:
                        # If conversion fails, return string representation
                        software_list.append(str(software_item))
            return software_list
        else:
            return []

    elif action == "list_softwares":
        results, _, err = client.zdx.inventory.list_softwares(query_params=query_params)
        if err:
            raise Exception(f"Software listing failed: {err}")

        # The ZDX SDK now returns a list of DeviceSoftwareInventory objects directly
        # (the software property from SoftwareList)
        if results:
            software_list = []
            for software_item in results:
                try:
                    # Convert each DeviceSoftwareInventory object to dictionary
                    if hasattr(software_item, 'as_dict'):
                        software_list.append(software_item.as_dict())
                    else:
                        # Fallback to dict conversion
                        software_list.append(dict(software_item))
                except Exception:
                    # If conversion fails, return string representation
                    software_list.append(str(software_item))
            return software_list
        else:
            return []

    else:
        raise ValueError("Invalid action. Must be one of: 'list_softwares', 'list_software_key'")
