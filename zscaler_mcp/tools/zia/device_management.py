"""
ZIA Device Management MCP Tools.

This module provides MCP tools for querying ZIA Device Management resources,
including devices and device groups. These are read-only operations for
retrieving device information managed by Zscaler Internet Access.

Device Management allows you to:
- Query all devices registered with ZIA
- List device groups for organizational management
- Filter devices by name, user, and other criteria
- Retrieve lightweight device lists for quick lookups
- View Cloud Browser Isolation (CBI) and Zscaler Client Connector (ZCC) devices

Dependencies:
    - Requires valid Zscaler credentials (ZSCALER_CLIENT_ID, ZSCALER_CLIENT_SECRET, ZSCALER_VANITY_DOMAIN)
    - Uses the zscaler-sdk-python device_management module

Related Tools:
    - zia_list_users: Get user information to filter devices by user_ids
    - zcc_list_devices: Alternative ZCC-specific device listing

Example Usage:
    # List all device groups
    groups = zia_list_device_groups()

    # List device groups with device info included
    groups_with_devices = zia_list_device_groups(include_device_info=True)

    # List all devices
    devices = zia_list_devices()

    # List devices with pagination
    devices_page1 = zia_list_devices(page=1, page_size=100)

    # Search devices by name prefix
    windows_devices = zia_list_devices(name="Windows")

    # Get lightweight device list
    device_ids = zia_list_devices_lite()
"""

import json
from typing import Annotated, Dict, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zia_list_device_groups(
    include_device_info: Annotated[
        Optional[bool],
        Field(
            description="Include or exclude device information in the response. "
            "When True, each device group includes its associated devices. "
            "Default is False for faster response."
        )
    ] = None,
    include_pseudo_groups: Annotated[
        Optional[bool],
        Field(
            description="Include or exclude Zscaler Client Connector (ZCC) and "
            "Cloud Browser Isolation (CBI) related device groups. "
            "Default is True to show all groups."
        )
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict]:
    """
    List ZIA device groups with optional filtering.

    Device groups are logical containers for organizing devices in ZIA.
    They can be used in policies to apply rules to specific sets of devices.

    Args:
        include_device_info: When True, includes detailed device information
            within each group. Set to False for faster response when you
            only need group metadata.
        include_pseudo_groups: When True, includes system-generated groups
            for Zscaler Client Connector (ZCC) and Cloud Browser Isolation (CBI).
            Set to False to only see user-created groups.
        use_legacy: Whether to use legacy API (default: False).
        service: The service identifier (default: "zia").

    Returns:
        List of device group dictionaries containing:
        - id: Unique identifier for the device group
        - name: Name of the device group
        - description: Description of the group
        - groupType: Type of the group (e.g., "ZCC", "CBI", custom)
        - deviceCount: Number of devices in the group (if include_device_info=True)
        - devices: List of devices (if include_device_info=True)
        - osType: Operating system type for the group
        - predefined: Whether this is a system-defined group

    Examples:
        >>> # List all device groups (basic info only)
        >>> groups = zia_list_device_groups()
        >>> for group in groups:
        ...     print(f"{group['name']}: {group.get('deviceCount', 'N/A')} devices")

        >>> # List device groups with full device details
        >>> groups = zia_list_device_groups(include_device_info=True)
        >>> for group in groups:
        ...     print(f"Group: {group['name']}")
        ...     for device in group.get('devices', []):
        ...         print(f"  - {device['name']}")

        >>> # List only custom device groups (exclude ZCC/CBI groups)
        >>> custom_groups = zia_list_device_groups(include_pseudo_groups=False)

        >>> # Get comprehensive view with all options enabled
        >>> all_groups = zia_list_device_groups(
        ...     include_device_info=True,
        ...     include_pseudo_groups=True
        ... )
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.device_management

    query_params = {}
    if include_device_info is not None:
        query_params["includeDeviceInfo"] = include_device_info
    if include_pseudo_groups is not None:
        query_params["includePseudoGroups"] = include_pseudo_groups

    groups, _, err = zia.list_device_groups(query_params=query_params if query_params else None)
    if err:
        raise Exception(f"Failed to list device groups: {err}")
    return [g.as_dict() for g in groups]


def zia_list_devices(
    name: Annotated[
        Optional[str],
        Field(
            description="Filter devices by name prefix (starts-with match). "
            "For example, 'Windows' matches 'Windows-PC-001', 'Windows-Laptop', etc."
        )
    ] = None,
    user_ids: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description="Filter devices by specific user IDs. Accepts a JSON array string "
            "or Python list of user ID strings. Example: '[\"12345\", \"67890\"]' or "
            "[\"12345\", \"67890\"]. Use zia_list_users to find user IDs."
        )
    ] = None,
    include_all: Annotated[
        Optional[bool],
        Field(
            description="Include or exclude Cloud Browser Isolation (CBI) devices. "
            "When True, CBI devices are included in the results. Default is True."
        )
    ] = None,
    page: Annotated[
        Optional[int],
        Field(
            description="Page number for pagination (1-based). Use with page_size to "
            "retrieve large device lists in chunks. Default starts at page 1."
        )
    ] = None,
    page_size: Annotated[
        Optional[int],
        Field(
            description="Number of devices per page. Default is 100, maximum is 1000. "
            "Use smaller values for faster responses, larger for fewer API calls."
        )
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict]:
    """
    List ZIA devices with comprehensive filtering and pagination options.

    Retrieves devices registered with Zscaler Internet Access. Supports filtering
    by device name, user ownership, and device type, with pagination for large
    device populations.

    Args:
        name: Filter by device name prefix (starts-with match). Case-insensitive.
            Use this to find devices by naming convention (e.g., "CORP-", "DEV-").
        user_ids: Filter to show only devices owned by specific users.
            Can be a JSON array string or Python list of user ID strings.
        include_all: When True, includes Cloud Browser Isolation (CBI) devices.
            Set to False to exclude virtual CBI devices from results.
        page: Page number for paginated results (1-based indexing).
        page_size: Number of results per page (default: 100, max: 1000).
        use_legacy: Whether to use legacy API (default: False).
        service: The service identifier (default: "zia").

    Returns:
        List of device dictionaries containing:
        - id: Unique device identifier
        - name: Device name
        - deviceGroupType: Type classification of the device
        - deviceModel: Hardware model information
        - osType: Operating system type (WINDOWS_OS, MAC_OS, IOS, ANDROID_OS, LINUX)
        - osVersion: Operating system version
        - owner_name: Name of the device owner
        - ownerUserId: User ID of the owner
        - description: Device description

    Examples:
        >>> # List all devices (first 100)
        >>> devices = zia_list_devices()
        >>> print(f"Found {len(devices)} devices")

        >>> # Search for Windows devices
        >>> windows_devices = zia_list_devices(name="Windows")

        >>> # Get devices for specific users
        >>> user_devices = zia_list_devices(user_ids='["12345", "67890"]')

        >>> # Paginate through large device lists
        >>> page1 = zia_list_devices(page=1, page_size=500)
        >>> page2 = zia_list_devices(page=2, page_size=500)

        >>> # Exclude CBI devices
        >>> physical_devices = zia_list_devices(include_all=False)

        >>> # Combined filtering: Windows devices for specific users, paginated
        >>> filtered = zia_list_devices(
        ...     name="CORP-WIN",
        ...     user_ids='["12345"]',
        ...     page=1,
        ...     page_size=50
        ... )

    Pagination Tips:
        - Use page_size=1000 for bulk exports (fewer API calls)
        - Use page_size=100 for interactive queries (faster response)
        - Keep track of result count to know when you've reached the last page
        - If len(results) < page_size, you've reached the last page
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.device_management

    query_params = {}

    if name:
        query_params["name"] = name

    if user_ids is not None:
        # Parse user_ids if provided as JSON string
        if isinstance(user_ids, str):
            try:
                user_ids = json.loads(user_ids)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON for user_ids: {e}")
        if not isinstance(user_ids, list):
            raise ValueError("user_ids must be a list of user ID strings")
        # Convert to comma-separated string for API
        query_params["userIds"] = ",".join(str(uid) for uid in user_ids)

    if include_all is not None:
        query_params["includeAll"] = include_all

    if page is not None:
        if page < 1:
            raise ValueError("page must be 1 or greater")
        query_params["page"] = page

    if page_size is not None:
        if page_size < 1 or page_size > 1000:
            raise ValueError("page_size must be between 1 and 1000")
        query_params["pageSize"] = page_size

    devices, _, err = zia.list_devices(query_params=query_params if query_params else None)
    if err:
        raise Exception(f"Failed to list devices: {err}")
    return [d.as_dict() for d in devices]


def zia_list_devices_lite(
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict]:
    """
    List ZIA devices in lightweight format (ID, name, owner only).

    Returns a simplified list of devices containing only essential fields.
    This is faster than the full device list and ideal for:
    - Quick device lookups by name
    - Building device selection dropdowns
    - Getting device IDs for other operations
    - Validating device existence

    Args:
        use_legacy: Whether to use legacy API (default: False).
        service: The service identifier (default: "zia").

    Returns:
        List of lightweight device dictionaries containing:
        - id: Unique device identifier
        - name: Device name
        - owner_name: Name of the device owner (if available)

    Examples:
        >>> # Get all devices (lightweight)
        >>> devices = zia_list_devices_lite()
        >>> print(f"Total devices: {len(devices)}")

        >>> # Build a device name to ID mapping
        >>> device_map = {d['name']: d['id'] for d in zia_list_devices_lite()}
        >>> laptop_id = device_map.get("CORP-LAPTOP-001")

        >>> # Quick count of all devices
        >>> device_count = len(zia_list_devices_lite())
        >>> print(f"Organization has {device_count} devices")

        >>> # Find devices owned by a specific person
        >>> devices = zia_list_devices_lite()
        >>> john_devices = [d for d in devices if d.get('owner_name') == 'John Doe']

    Performance Note:
        This endpoint returns minimal data and is significantly faster than
        zia_list_devices() when you only need device identifiers. Use this
        for lookups and zia_list_devices() when you need full device details.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.device_management

    devices, _, err = zia.list_device_lite()
    if err:
        raise Exception(f"Failed to list devices (lite): {err}")
    return [d.as_dict() for d in devices]
