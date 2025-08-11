from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zdx_get_application_metric(
    app_id: Annotated[
        str, Field(description="The unique ID for the ZDX application.")
    ],
    metric_name: Annotated[
        Optional[Literal["pft", "dns", "availability"]],
        Field(description="The name of the metric to return. Available values: 'pft' (Page Fetch Time), 'dns' (DNS Time), 'availability'.")
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
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> List[Dict[str, Any]]:
    """
    Tool for retrieving ZDX metrics for a specified application configured within the ZDX tenant.

    Returns detailed metrics for the specified application, including performance indicators
    such as Page Fetch Time (PFT), DNS Time, and availability metrics. Supports various
    filtering options to focus on specific locations, departments, or time ranges.

    Args:
        app_id: The unique ID for the ZDX application.
        metric_name: Optional metric name to filter results. Available values:
            - 'pft': Page Fetch Time metrics
            - 'dns': DNS Time metrics
            - 'availability': Availability metrics
        location_id: Optional list of location IDs to filter by specific locations.
        department_id: Optional list of department IDs to filter by specific departments.
        geo_id: Optional list of geolocation IDs to filter by geographic regions.
        since: Optional number of hours to look back for application data (default 2 hours).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        List of dictionaries containing application metrics data.

    Raises:
        Exception: If the application metrics retrieval fails due to API errors.

    Examples:
        Get all metrics for a specific application:
        >>> metrics = zdx_get_application_metric(app_id="999999999")

        Get DNS metrics for a specific application:
        >>> dns_metrics = zdx_get_application_metric(
        ...     app_id="999999999",
        ...     metric_name="dns"
        ... )

        Get Page Fetch Time metrics for the past 24 hours:
        >>> pft_metrics = zdx_get_application_metric(
        ...     app_id="999999999",
        ...     metric_name="pft",
        ...     since=24
        ... )

        Get availability metrics for a specific location:
        >>> availability_metrics = zdx_get_application_metric(
        ...     app_id="999999999",
        ...     metric_name="availability",
        ...     location_id=["888888888"]
        ... )

        Get DNS metrics with multiple filters:
        >>> dns_metrics = zdx_get_application_metric(
        ...     app_id="999999999",
        ...     metric_name="dns",
        ...     since=24,
        ...     location_id=["888888888"],
        ...     department_id=["123456"],
        ...     geo_id=["US"]
        ... )
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    query_params = {}
    if metric_name:
        query_params["metric_name"] = metric_name
    if location_id:
        query_params["location_id"] = location_id
    if department_id:
        query_params["department_id"] = department_id
    if geo_id:
        query_params["geo_id"] = geo_id
    if since:
        query_params["since"] = since

    results, _, err = client.zdx.apps.get_app_metrics(
        app_id, query_params=query_params
    )
    if err:
        raise Exception(f"Application metrics retrieval failed: {err}")

    # The ZDX SDK returns a list of ApplicationMetrics objects
    if results:
        return [metric.as_dict() for metric in results]
    else:
        return []
