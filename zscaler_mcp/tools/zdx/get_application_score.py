from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zdx_get_application_score(
    action: Annotated[
        Literal["read_app", "read_app_score"],
        Field(description="Must be one of 'read_app' or 'read_app_score'."),
    ],
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
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Tool for retrieving ZDX application scores and score trends.

    Supports two actions:
    - read_app: Returns information on the application's ZDX Score (for the previous 2 hours),
      including most impacted locations and the total number of users impacted.
    - read_app_score: Returns the ZDX score trend for the specified application configured
      within the ZDX tenant.

    Args:
        action: The type of score information to retrieve ('read_app' or 'read_app_score').
        app_id: The unique ID for the ZDX application.
        location_id: Optional list of location IDs to filter by specific locations.
        department_id: Optional list of department IDs to filter by specific departments.
        geo_id: Optional list of geolocation IDs to filter by geographic regions.
        since: Optional number of hours to look back for application data (default 2 hours).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        For 'read_app': Dictionary containing application score information.
        For 'read_app_score': List of dictionaries containing application score trend data.

    Raises:
        Exception: If the application score retrieval fails due to API errors.

    Examples:
        Get application score for a specific application:
        >>> score_info = zdx_list_application_score(action="read_app", app_id="999999999")

        Get application score trend for a specific application:
        >>> score_trend = zdx_list_application_score(action="read_app_score", app_id="999999999")

        Get application score with location filter:
        >>> score_info = zdx_list_application_score(
        ...     action="read_app",
        ...     app_id="999999999",
        ...     location_id=["125584"]
        ... )

        Get application score trend for the past 10 hours:
        >>> score_trend = zdx_list_application_score(
        ...     action="read_app_score",
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

    if action == "read_app":
        """
        Returns information on the application's ZDX Score (for the previous 2 hours).
        Including most impacted locations, and the total number of users impacted.
        """
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

    elif action == "read_app_score":
        """
        Returns the ZDX score trend for the specified application configured within the ZDX tenant.
        """
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

    else:
        raise ValueError("Invalid action. Must be one of: 'read_app', 'read_app_score'")
