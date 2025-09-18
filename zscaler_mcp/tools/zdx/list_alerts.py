from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zdx_list_alerts(
    action: Annotated[
        Literal["read", "read_alert", "read_affected_devices"],
        Field(description="Must be one of 'read', 'read_alert', or 'read_affected_devices'."),
    ],
    alert_id: Annotated[
        Optional[str], Field(description="Required if action is 'read_alert' or 'read_affected_devices'. The unique ID for the alert.")
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
    location_groups: Annotated[
        Optional[List[int]], Field(description="Filter by location group ID(s). Only available for read_affected_devices action.")
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
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Tool for retrieving ZDX alert information and managing alert-related data.
    
    Supports three actions:
    - read: Returns a list of all ongoing alert rules across an organization (USE THIS FOR GENERAL ALERT OVERVIEW).
    - read_alert: Returns details of a single alert including impacted department, locations, and alert trigger (USE FOR SPECIFIC ALERT DETAILS).
    - read_affected_devices: Returns a list of all affected devices associated with an alert rule (USE FOR ALERT IMPACT ANALYSIS).
    
    USAGE GUIDELINES:
    - Use action='read' by default to get an overview of all ongoing alerts in the organization
    - Use action='read_alert' when you need detailed information about a specific alert
    - Use action='read_affected_devices' when you need to analyze the impact of a specific alert on devices
    
    Args:
        action: The type of alert information to retrieve ('read', 'read_alert', or 'read_affected_devices').
        alert_id: Required if action is 'read_alert' or 'read_affected_devices'. The unique ID for the alert.
        location_id: Optional list of location IDs to filter by specific locations.
        department_id: Optional list of department IDs to filter by specific departments.
        geo_id: Optional list of geolocation IDs to filter by geographic regions.
        location_groups: Optional list of location group IDs (only available for read_affected_devices action).
        since: Optional number of hours to look back (default 2 hours, max 14 days).
        offset: Optional pagination offset for getting next batch of results.
        limit: Optional number of items to return per request (minimum 1).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").
        
    Returns:
        For 'read': List of dictionaries containing ongoing alert information.
        For 'read_alert': Dictionary containing detailed alert information.
        For 'read_affected_devices': List of dictionaries containing affected device information.
        
    Raises:
        Exception: If the alert information retrieval fails due to API errors.
        
    Examples:
        DEFAULT USAGE - Get overview of all ongoing alerts in the organization:
        >>> alerts = zdx_list_alerts(action="read")
        
        Get ongoing alerts for the past 24 hours:
        >>> alerts = zdx_list_alerts(
        ...     action="read", 
        ...     since=24
        ... )
        
        Get ongoing alerts for specific locations:
        >>> alerts = zdx_list_alerts(
        ...     action="read", 
        ...     location_id=["58755", "58756"]
        ... )
        
        Get ongoing alerts with pagination:
        >>> alerts = zdx_list_alerts(
        ...     action="read", 
        ...     limit=50, 
        ...     offset="next_offset_value"
        ... )
        
        SPECIFIC ALERT QUERY - Get detailed information for a specific alert:
        >>> alert_details = zdx_list_alerts(
        ...     action="read_alert", 
        ...     alert_id="7473160764821179371"
        ... )
        
        ALERT IMPACT ANALYSIS - Get affected devices for a specific alert:
        >>> affected_devices = zdx_list_alerts(
        ...     action="read_affected_devices", 
        ...     alert_id="7473160764821179371"
        ... )
        
        Get affected devices for the past 24 hours:
        >>> affected_devices = zdx_list_alerts(
        ...     action="read_affected_devices", 
        ...     alert_id="7473160764821179371", 
        ...     since=24
        ... )
        
        Get affected devices with location filtering:
        >>> affected_devices = zdx_list_alerts(
        ...     action="read_affected_devices", 
        ...     alert_id="7473160764821179371", 
        ...     location_id=["58755"], 
        ...     department_id=["123456"]
        ... )
        
        Get affected devices with location groups:
        >>> affected_devices = zdx_list_alerts(
        ...     action="read_affected_devices", 
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
    if location_groups and action == "read_affected_devices":
        query_params["location_groups"] = location_groups

    if action == "read_alert":
        """
        Returns details of a single alert including the impacted department,
        Zscaler locations, geolocation, and alert trigger.
        """
        if not alert_id:
            raise ValueError("alert_id is required for action=read_alert")
        result, _, err = client.zdx.alerts.get_alert(alert_id)
        if err:
            raise Exception(f"Alert lookup failed: {err}")
        
        # The ZDX SDK returns a single AlertDetails object
        if result:
            return result.as_dict()
        else:
            return {}

    elif action == "read_affected_devices":
        """
        Returns a list of all affected devices associated with an alert rule.
        """
        if not alert_id:
            raise ValueError("alert_id is required for action=read_affected_devices")
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

    elif action == "read":
        """
        Returns a list of all ongoing alert rules across an organization in ZDX.
        """
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

    else:
        raise ValueError("Invalid action. Must be one of: 'read', 'read_alert', 'read_affected_devices'")