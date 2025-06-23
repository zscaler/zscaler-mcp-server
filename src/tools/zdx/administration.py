from src.sdk.zscaler_client import get_zscaler_client
from typing import Union, List, Dict, Any

def zdx_admin_discovery_tool(
    query_type: str,
    search: str = None,
    since: int = None,
    use_legacy: bool = False,
    service: str = "zdx",
) -> Union[List[Dict[str, Any]], str]:
    """
    Tool for discovering ZDX departments or locations.

    This tool allows searching for:
    - Departments (e.g., IT, Finance)
    - Locations (e.g., San Francisco, London)

    based on optional query parameters like `search` and `since`.

    Args:
        query_type (str): Must be either `"departments"` or `"locations"`.
        search (str, optional): Search term to filter results by name or ID.
        since (int, optional): Number of hours to look back for devices (default 2 hours if not provided).

    Returns:
        Union[List[Dict[str, Any]], str]: A list of department or location records, or an error message.

    Examples:
        Search departments by name:
        >>> zdx_admin_discovery_tool(..., query_type="departments", search="Finance")

        Search locations by name:
        >>> zdx_admin_discovery_tool(..., query_type="locations", search="Vancouver")

        Fetch all locations seen in the last 4 hours:
        >>> zdx_admin_discovery_tool(..., query_type="locations", since=4)

    Notes:
        - The results are paginated internally by the SDK.
        - Ensure `query_type` is accurately set to `"departments"` or `"locations"` for proper routing.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    query_params = {}
    if search:
        query_params["search"] = search
    if since:
        query_params["since"] = since

    if query_type.lower() == "departments":
        departments, _, err = client.zdx.admin.list_departments(query_params=query_params)
        if err:
            raise Exception(f"Error retrieving departments: {err}")
        return [d.as_dict() for d in departments]

    elif query_type.lower() == "locations":
        locations, _, err = client.zdx.admin.list_locations(query_params=query_params)
        if err:
            raise Exception(f"Error retrieving locations: {err}")
        return [l.as_dict() for l in locations]

    else:
        raise ValueError("Invalid query_type. Must be either 'departments' or 'locations'.")
