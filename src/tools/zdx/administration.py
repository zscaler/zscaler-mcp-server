from src.sdk.zscaler_client import get_zscaler_client
from src.zscaler_mcp import app
from typing import Annotated, Union, List, Dict, Any, Optional, Literal
from pydantic import Field


@app.tool(
    name="zdx_admin_discovery_tool",
    description="Tool for discovering ZDX departments or locations.",
)
def zdx_admin_discovery_tool(
    query_type: Annotated[
        Literal["departments", "locations"],
        Field(description="Must be either 'departments' or 'locations'.")
    ],
    search: Annotated[
        Optional[str],
        Field(description="Search term to filter results by name or ID.")
    ] = None,
    since: Annotated[
        Optional[int],
        Field(description="Number of hours to look back for devices (default 2 hours if not provided).")
    ] = None,
    use_legacy: Annotated[
        bool,
        Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[
        str,
        Field(description="The service to use.")
    ] = "zdx",
) -> Union[List[Dict[str, Any]], str]:
    """
    Tool for discovering ZDX departments or locations.

    This tool allows searching for:
    - Departments (e.g., IT, Finance)
    - Locations (e.g., San Francisco, London)

    based on optional query parameters like `search` and `since`.
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
