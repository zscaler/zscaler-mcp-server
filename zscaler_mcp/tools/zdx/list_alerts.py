from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# ============================================================================
# READ-ONLY OPERATIONS
# ============================================================================

def zdx_list_alerts(
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
        Optional[int], Field(description="Number of hours to look back (default 2h). Cannot exceed 14 days.")
    ] = None,
    offset: Annotated[
        Optional[str], Field(description="The next_offset value from the last request for pagination.")
    ] = None,
    limit: Annotated[
        Optional[int], Field(description="Number of items to return per request (minimum 1).")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> List[Dict[str, Any]]:
    """
    Lists all ongoing ZDX alert rules across an organization.
    This is a read-only operation.

    Returns a list of all ongoing alert rules. This is the default operation for getting
    an overview of all alerts in the organization. Supports filtering by location, department,
    geolocation, and time range.

    Args:
        location_id: Optional list of location IDs to filter by specific locations.
        department_id: Optional list of department IDs to filter by specific departments.
        geo_id: Optional list of geolocation IDs to filter by geographic regions.
        since: Optional number of hours to look back (default 2 hours, max 14 days).
        offset: Optional pagination offset for getting next batch of results.
        limit: Optional number of items to return per request (minimum 1).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        List of dictionaries containing ongoing alert information.

    Raises:
        Exception: If the alert listing fails due to API errors.

    Examples:
        Get overview of all ongoing alerts:
        >>> alerts = zdx_list_alerts()

        Get alerts for the past 24 hours:
        >>> alerts = zdx_list_alerts(since=24)

        Get alerts for specific locations:
        >>> alerts = zdx_list_alerts(location_id=["58755", "58756"])

        Get alerts with pagination:
        >>> alerts = zdx_list_alerts(limit=50, offset="next_offset_value")
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
    if offset:
        query_params["offset"] = offset
    if limit:
        query_params["limit"] = limit

    result, _, err = client.zdx.alerts.read(query_params=query_params)
    if err:
        raise Exception(f"Ongoing alerts listing failed: {err}")

    # The ZDX SDK returns a list containing a single Alerts object
    if result and len(result) > 0:
        alerts_obj = result[0]  # Get the first (and only) Alerts object
        # Access the alerts property which contains a list of alert objects
        alerts_list = alerts_obj.alerts if hasattr(alerts_obj, 'alerts') else []
        return [alert.as_dict() for alert in alerts_list]
    else:
        return []


def zdx_get_alert(
    alert_id: Annotated[
        str, Field(description="The unique ID for the alert.")
    ],
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> Dict[str, Any]:
    """
    Gets detailed information for a specific ZDX alert.
    This is a read-only operation.

    Returns details of a single alert including the impacted department,
    Zscaler locations, geolocation, and alert trigger. Use this when you need
    detailed information about a specific alert.

    Args:
        alert_id: The unique ID for the alert (required).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        Dictionary containing detailed alert information.

    Raises:
        Exception: If the alert lookup fails due to API errors.

    Examples:
        Get detailed information for a specific alert:
        >>> alert = zdx_get_alert(alert_id="7473160764821179371")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    result, _, err = client.zdx.alerts.get_alert(alert_id)
    if err:
        raise Exception(f"Alert lookup failed: {err}")

    # The ZDX SDK returns a single AlertDetails object
    if result:
        return result.as_dict()
    else:
        return {}


def zdx_list_alert_affected_devices(
    alert_id: Annotated[
        str, Field(description="The unique ID for the alert.")
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
    location_groups: Annotated[
        Optional[List[int]], Field(description="Filter by location group ID(s).")
    ] = None,
    since: Annotated[
        Optional[int], Field(description="Number of hours to look back (default 2h). Cannot exceed 14 days.")
    ] = None,
    offset: Annotated[
        Optional[str], Field(description="The next_offset value from the last request for pagination.")
    ] = None,
    limit: Annotated[
        Optional[int], Field(description="Number of items to return per request (minimum 1).")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> List[Dict[str, Any]]:
    """
    Lists all devices affected by a specific ZDX alert.
    This is a read-only operation.

    Returns a list of all affected devices associated with an alert rule.
    Use this when you need to analyze the impact of a specific alert on devices.
    Supports filtering by location, department, geolocation, and location groups.

    Args:
        alert_id: The unique ID for the alert (required).
        location_id: Optional list of location IDs to filter by specific locations.
        department_id: Optional list of department IDs to filter by specific departments.
        geo_id: Optional list of geolocation IDs to filter by geographic regions.
        location_groups: Optional list of location group IDs.
        since: Optional number of hours to look back (default 2 hours, max 14 days).
        offset: Optional pagination offset for getting next batch of results.
        limit: Optional number of items to return per request (minimum 1).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        List of dictionaries containing affected device information.

    Raises:
        Exception: If the affected devices lookup fails due to API errors.

    Examples:
        Get affected devices for an alert:
        >>> devices = zdx_list_alert_affected_devices(alert_id="7473160764821179371")

        Get affected devices for the past 24 hours:
        >>> devices = zdx_list_alert_affected_devices(
        ...     alert_id="7473160764821179371",
        ...     since=24
        ... )

        Get affected devices with location filtering:
        >>> devices = zdx_list_alert_affected_devices(
        ...     alert_id="7473160764821179371",
        ...     location_id=["58755"],
        ...     department_id=["123456"]
        ... )

        Get affected devices with location groups:
        >>> devices = zdx_list_alert_affected_devices(
        ...     alert_id="7473160764821179371",
        ...     location_groups=[1, 2]
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
    if since:
        query_params["since"] = since
    if offset:
        query_params["offset"] = offset
    if limit:
        query_params["limit"] = limit
    if location_groups:
        query_params["location_groups"] = location_groups

    result, _, err = client.zdx.alerts.read_affected_devices(
        alert_id, query_params=query_params
    )
    if err:
        raise Exception(f"Affected devices lookup failed: {err}")

    # The ZDX SDK returns a list containing a single AffectedDevices object
    if result and len(result) > 0:
        affected_devices_obj = result[0]  # Get the first (and only) AffectedDevices object
        # Access the devices property which contains a list of device objects
        devices_list = affected_devices_obj.devices if hasattr(affected_devices_obj, 'devices') else []
        return [device.as_dict() for device in devices_list]
    else:
        return []
