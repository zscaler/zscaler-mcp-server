from src.sdk.zscaler_client import get_zscaler_client
from typing import Union


def trusted_network_manager(
    action: str,
    network_id: str = None,
    name: str = None,
    query_params: dict = None,
    use_legacy: bool = False,
    service: str = "zpa",
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
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.zpa.trusted_networks

    if action == "read":
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

    raise ValueError(f"Unsupported action: {action}")
