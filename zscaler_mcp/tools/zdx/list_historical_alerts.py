from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zdx_list_historical_alerts(
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
    Tool for retrieving ZDX historical alert information.
    
    Returns a list of alert history rules defined across an organization.
    All alert history rules are returned if the search filter is not specified.
    The default is set to the previous 2 hours.
    Alert history rules have an Ended On date.
    
    Note: Cannot exceed the 14-day time range limit for alert rules.
    
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
        List of dictionaries containing historical alert information.
        
    Raises:
        Exception: If the historical alert information retrieval fails due to API errors.
        
    Examples:
        Get all alert history rules for the past 2 hours:
        >>> historical_alerts = zdx_list_historical_alerts()
        
        Get alert history rules for the past 24 hours:
        >>> historical_alerts = zdx_list_historical_alerts(since=24)
        
        Get alert history rules for specific locations:
        >>> historical_alerts = zdx_list_historical_alerts(
        ...     location_id=["58755", "58756"]
        ... )
        
        Get alert history rules for specific departments:
        >>> historical_alerts = zdx_list_historical_alerts(
        ...     department_id=["123456", "789012"]
        ... )
        
        Get alert history rules with pagination:
        >>> historical_alerts = zdx_list_historical_alerts(
        ...     limit=50, 
        ...     offset="next_offset_value"
        ... )
        
        Get alert history rules with multiple filters:
        >>> historical_alerts = zdx_list_historical_alerts(
        ...     since=24,
        ...     location_id=["58755"],
        ...     department_id=["123456"],
        ...     geo_id=["US"],
        ...     limit=100
        ... )
        
        Get alert history rules for a specific time range (within 14-day limit):
        >>> historical_alerts = zdx_list_historical_alerts(
        ...     since=336  # 14 days * 24 hours
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

    result, _, err = client.zdx.alerts.list_historical(query_params=query_params)
    if err:
        raise Exception(f"Historical alerts listing failed: {err}")
    
    # The ZDX SDK returns a list containing a single Alerts object
    if result and len(result) > 0:
        alerts_obj = result[0]  # Get the first (and only) Alerts object
        # Access the alerts property which contains a list of alert objects
        alerts_list = alerts_obj.alerts if hasattr(alerts_obj, 'alerts') else []
        return [alert.as_dict() for alert in alerts_list]
    else:
        return []
