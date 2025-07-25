from src.sdk.zscaler_client import get_zscaler_client
from src.zscaler_mcp import app
from typing import Annotated, Union, List, Optional
from pydantic import Field


@app.tool(
    name="zcc_list_devices",
    description="Retrieves ZCC device enrollment information from the Zscaler Client Connector Portal.",
)
def zcc_devices_v1_manager(
    username: Annotated[
        Optional[str],
        Field(description="Username to filter by (e.g., 'jdoe@acme.com').")
    ] = None,
    os_type: Annotated[
        Optional[str],
        Field(description="Device operating system type. Valid options: ios, android, windows, macos, linux.")
    ] = None,
    page: Annotated[
        Optional[int],
        Field(description="Page number for paginated results.")
    ] = None,
    page_size: Annotated[
        Optional[int],
        Field(description="Number of results per page. Default is 50. Max is 5000.")
    ] = None,
    use_legacy: Annotated[
        bool,
        Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[
        str,
        Field(description="The service to use.")
    ] = "zcc",
) -> Union[List[dict], str]:
    """
    Retrieves ZCC device enrollment information from the Zscaler Client Connector Portal.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    query_params = {}
    if username:
        query_params["username"] = username
    if os_type:
        query_params["os_type"] = os_type
    if page:
        query_params["page"] = page
    if page_size:
        query_params["page_size"] = page_size

    devices, _, err = client.zcc.devices.list_devices(query_params=query_params)
    if err:
        raise Exception(f"Error listing ZCC devices: {err}")
    return [d.as_dict() for d in devices]
