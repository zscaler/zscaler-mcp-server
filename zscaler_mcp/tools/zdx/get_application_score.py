from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# ============================================================================
# READ-ONLY OPERATIONS
# ============================================================================

def zdx_get_application(
    app_id: Annotated[
        str, Field(description="The unique ID for the ZDX application.")
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
    Gets ZDX score information for a specific application.
    This is a read-only operation.

    Returns information on the application's ZDX Score (for the previous 2 hours),
    including most impacted locations and the total number of users impacted.

    Args:
        app_id: The unique ID for the ZDX application (required).
        location_id: Optional list of location IDs to filter by specific locations.
        department_id: Optional list of department IDs to filter by specific departments.
        geo_id: Optional list of geolocation IDs to filter by geographic regions.
        since: Optional number of hours to look back for application data (default 2 hours).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        Dictionary containing application score information.

    Raises:
        Exception: If the application score retrieval fails due to API errors.

    Examples:
        Get application score:
        >>> score = zdx_get_application(app_id="999999999")

        Get application score with location filter:
        >>> score = zdx_get_application(
        ...     app_id="999999999",
        ...     location_id=["125584"]
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

    result, _, err = client.zdx.apps.get_app(
        app_id, query_params=query_params
    )
    if err:
        raise Exception(f"Application score lookup failed: {err}")

    # The ZDX SDK returns a list containing a single ApplicationScore object
    if result and len(result) > 0:
        app_obj = result[0]  # Get the first (and only) ApplicationScore object
        return app_obj.as_dict()
    else:
        return {}


def zdx_get_application_score_trend(
    app_id: Annotated[
        str, Field(description="The unique ID for the ZDX application.")
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
    Gets ZDX score trend for a specific application.
    This is a read-only operation.

    Returns the ZDX score trend for the specified application configured within the ZDX tenant.
    Shows how the application's performance score has changed over time.

    Args:
        app_id: The unique ID for the ZDX application (required).
        location_id: Optional list of location IDs to filter by specific locations.
        department_id: Optional list of department IDs to filter by specific departments.
        geo_id: Optional list of geolocation IDs to filter by geographic regions.
        since: Optional number of hours to look back for application data (default 2 hours).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        Dictionary containing application score trend data.

    Raises:
        Exception: If the application score trend retrieval fails due to API errors.

    Examples:
        Get application score trend:
        >>> trend = zdx_get_application_score_trend(app_id="999999999")

        Get score trend for the past 10 hours:
        >>> trend = zdx_get_application_score_trend(
        ...     app_id="999999999",
        ...     since=10
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

    result, _, err = client.zdx.apps.get_app_score(
        app_id, query_params=query_params
    )
    if err:
        raise Exception(f"Application score trend lookup failed: {err}")

    # The ZDX SDK returns a list containing a single ApplicationScoreTrend object
    if result and len(result) > 0:
        app_obj = result[0]  # Get the first (and only) ApplicationScoreTrend object
        return app_obj.as_dict()
    else:
        return {}
