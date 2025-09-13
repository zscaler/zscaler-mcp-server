from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zdx_get_application_user(
    action: Annotated[
        Literal["list_app_users", "read_app_user"],
        Field(description="Must be one of 'list_app_users' or 'read_app_user'."),
    ],
    app_id: Annotated[
        str, Field(description="The unique ID for the ZDX application.")
    ],
    user_id: Annotated[
        Optional[str], Field(description="Required if action is 'read_app_user'. The unique ID for the ZDX user.")
    ] = None,
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
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Tool for retrieving ZDX application user information and device details.
    
    Supports two actions:
    - list_app_users: Returns a list of users and devices that were used to access the specified application.
    - read_app_user: Returns detailed information on a specific user and device that accessed the application.
    
    Args:
        action: The type of user information to retrieve ('list_app_users' or 'read_app_user').
        app_id: The unique ID for the ZDX application.
        user_id: Required if action is 'read_app_user'. The unique ID for the ZDX user.
        score_bucket: Optional ZDX score bucket filter. Available values:
            - 'poor': Score range 0-33
            - 'okay': Score range 34-65
            - 'good': Score range 66-100
        location_id: Optional list of location IDs to filter by specific locations.
        department_id: Optional list of department IDs to filter by specific departments.
        geo_id: Optional list of geolocation IDs to filter by geographic regions.
        since: Optional number of hours to look back for user data (default 2 hours).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").
        
    Returns:
        For 'list_app_users': List of dictionaries containing user and device information.
        For 'read_app_user': Dictionary containing detailed user and device information.
        
    Raises:
        Exception: If the application user information retrieval fails due to API errors.
        
    Examples:
        List all users and devices that accessed a specific application:
        >>> users = zdx_get_application_user(action="list_app_users", app_id="999999999")
        
        Get detailed information for a specific user:
        >>> user_details = zdx_get_application_user(
        ...     action="read_app_user", 
        ...     app_id="888888888", 
        ...     user_id="24328827"
        ... )
        
        List users with poor performance scores:
        >>> poor_users = zdx_get_application_user(
        ...     action="list_app_users", 
        ...     app_id="999999999", 
        ...     score_bucket="poor"
        ... )
        
        List users from a specific location:
        >>> location_users = zdx_get_application_user(
        ...     action="list_app_users", 
        ...     app_id="999999999", 
        ...     location_id=["545845"]
        ... )
        
        Get user details for the past 2 hours:
        >>> user_details = zdx_get_application_user(
        ...     action="read_app_user", 
        ...     app_id="888888888", 
        ...     user_id="24328827", 
        ...     since=2
        ... )
        
        List users with multiple filters:
        >>> filtered_users = zdx_get_application_user(
        ...     action="list_app_users", 
        ...     app_id="999999999", 
        ...     score_bucket="good", 
        ...     location_id=["545845"], 
        ...     department_id=["123456"], 
        ...     since=24
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

    if action == "read_app_user":
        """
        Returns information on the specified user and device that was used to access the specified application.
        """
        if not user_id:
            raise ValueError("user_id is required for action=read_app_user")
        result, _, err = client.zdx.apps.get_app_user(
            app_id, user_id, query_params=query_params
        )
        if err:
            raise Exception(f"Application user lookup failed: {err}")
        
        # The ZDX SDK returns a list containing a single ApplicationUserDetails object
        if result and len(result) > 0:
            user_obj = result[0]  # Get the first (and only) ApplicationUserDetails object
            return user_obj.as_dict()
        else:
            return {}

    elif action == "list_app_users":
        """
        Returns a list of users and devices that were used to access the specified application.
        """
        result, _, err = client.zdx.apps.list_app_users(
            app_id, query_params=query_params
        )
        if err:
            raise Exception(f"Application users listing failed: {err}")
        
        # The ZDX SDK returns a list containing a single ApplicationActiveUsers object
        if result and len(result) > 0:
            users_obj = result[0]  # Get the first (and only) ApplicationActiveUsers object
            # Access the users property which contains a list of user objects
            users_list = users_obj.users if hasattr(users_obj, 'users') else []
            return [user.as_dict() for user in users_list]
        else:
            return []

    else:
        raise ValueError("Invalid action. Must be one of: 'list_app_users', 'read_app_user'")
