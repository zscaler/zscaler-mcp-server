from typing import Annotated, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def trusted_network_manager(
    action: Annotated[
        str,
        Field(description="Action to perform. Must be 'read'."),
    ],
    network_id: Annotated[
        str,
        Field(description="If provided, retrieves trusted network by ID."),
    ] = None,
    name: Annotated[
        str,
        Field(
            description="If provided, will be used to search for the trusted network."
        ),
    ] = None,
    query_params: Annotated[
        dict,
        Field(description="Optional query parameters for filtering results."),
    ] = None,
    use_legacy: Annotated[
        bool,
        Field(description="Whether to use the legacy API."),
    ] = False,
    service: Annotated[
        str,
        Field(description="The service to use."),
    ] = "zpa",
) -> Union[dict, list[dict], str]:
    """
    Tool for retrieving ZPA Trusted Networks.

    Supported actions:
    - read: Fetch all trusted networks or one by ID or name.

    Args:
        action (str): 'read'
        name (str): If provided, will be used to search for the trusted network.
        network_id (str): If provided, retrieves trusted network by ID.

    Returns:
        Union[dict, list[dict], str]: Trusted network(s) data.
    """
    if action != "read":
        raise ValueError("Only 'read' action is supported")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.trusted_networks
    query_params = query_params or {}

    # Fetch by network ID
    if network_id:
        result, _, err = api.get_network(network_id)
        if err:
            raise Exception(f"Failed to fetch trusted network {network_id}: {err}")
        return result.as_dict()

    # Fetch by name if provided
    if name:
        query_params["search"] = name
        networks, _, err = api.list_trusted_networks(query_params=query_params)
        if err:
            raise Exception(f"Failed to search trusted networks by name: {err}")
        matched = next((n for n in networks if n.name == name), None)
        if not matched:
            raise Exception(f"No trusted network found with name '{name}'")
        return matched.as_dict()

    # List all trusted networks
    networks, _, err = api.list_trusted_networks(query_params=query_params)
    if err:
        raise Exception(f"Failed to list trusted networks: {err}")
    return [n.as_dict() for n in networks]
