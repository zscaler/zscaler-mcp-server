from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# ============================================================================
# READ-ONLY OPERATIONS
# ============================================================================

def zdx_list_application_users(
    app_id: Annotated[
        str, Field(description="The unique ID for the ZDX application.")
    ],
    score_bucket: Annotated[
        Optional[Literal["poor", "okay", "good"]], 
        Field(description="The ZDX score bucket to filter by. Available values: 'poor' (0-33), 'okay' (34-65), 'good' (66-100).")
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
    Lists users and devices that accessed a specific ZDX application.
    This is a read-only operation.

    Returns a list of users and devices that were used to access the specified application.
    Supports filtering by performance score bucket, location, department, and time range.

    Args:
        app_id: The unique ID for the ZDX application (required).
        score_bucket: Optional ZDX score bucket filter ('poor': 0-33, 'okay': 34-65, 'good': 66-100).
        location_id: Optional list of location IDs to filter by specific locations.
        department_id: Optional list of department IDs to filter by specific departments.
        geo_id: Optional list of geolocation IDs to filter by geographic regions.
        since: Optional number of hours to look back for user data (default 2 hours).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        List of dictionaries containing user and device information.

    Raises:
        Exception: If the application user retrieval fails due to API errors.

    Examples:
        List all users for an application:
        >>> users = zdx_list_application_users(app_id="999999999")

        List users with poor performance:
        >>> poor_users = zdx_list_application_users(
        ...     app_id="999999999",
        ...     score_bucket="poor"
        ... )
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    query_params = {}
    if score_bucket:
        query_params["score_bucket"] = score_bucket
    if location_id:
        query_params["location_id"] = location_id
    if department_id:
        query_params["department_id"] = department_id
    if geo_id:
        query_params["geo_id"] = geo_id
    if since:
        query_params["since"] = since

    result, _, err = client.zdx.apps.list_users(app_id, query_params=query_params)
    if err:
        raise Exception(f"Application user listing failed: {err}")

    if result and len(result) > 0:
        users_obj = result[0]
        users_list = users_obj.users if hasattr(users_obj, 'users') else []
        return [user.as_dict() for user in users_list]
    else:
        return []


def zdx_get_application_user(
    app_id: Annotated[
        str, Field(description="The unique ID for the ZDX application.")
    ],
    user_id: Annotated[
        str, Field(description="The unique ID for the ZDX user.")
    ],
    since: Annotated[
        Optional[int], Field(description="Number of hours to look back (default 2h).")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> Dict[str, Any]:
    """
    Gets detailed information for a specific user accessing an application.
    This is a read-only operation.

    Returns detailed information on a specific user and device that accessed the application,
    including performance metrics and device details.

    Args:
        app_id: The unique ID for the ZDX application (required).
        user_id: The unique ID for the ZDX user (required).
        since: Optional number of hours to look back for user data (default 2 hours).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        Dictionary containing detailed user and device information.

    Raises:
        Exception: If the user lookup fails due to API errors.

    Examples:
        Get specific user details:
        >>> user = zdx_get_application_user(
        ...     app_id="888888888",
        ...     user_id="24328827"
        ... )
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    query_params = {}
    if since:
        query_params["since"] = since

    result, _, err = client.zdx.apps.get_user(app_id, user_id, query_params=query_params)
    if err:
        raise Exception(f"Application user lookup failed: {err}")

    if result:
        return result.as_dict()
    else:
        return {}
