from typing import Optional, Union, Literal, Annotated
import json
from sdk.zscaler_client import get_zscaler_client


def zia_ip_source_group_manager(
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    action: Annotated[
        Literal["get", "list", "add", "update", "delete"],
        "Action to perform: list, get, add, update, or delete.",
    ] = "list",
    group_id: Annotated[
        Optional[Union[int, str]],
        "Required for get, update, and delete actions.",
    ] = None,
    name: Annotated[
        Optional[str],
        "Group name (required for add/update).",
    ] = None,
    description: Annotated[
        Optional[str],
        "Group description (optional for add/update).",
    ] = None,
    ip_addresses: Annotated[
        Optional[Union[list[str], str]],
        "List of IP addresses (required for add/update). Accepts JSON string or list.",
    ] = None,
    search: Annotated[
        Optional[str],
        "Optional search string for filtering list results.",
    ] = None,
) -> Union[dict, list[dict], str]:
    """
    Performs CRUD operations on ZIA IP Source Groups.

    Args:
        cloud (str): Zscaler cloud environment.
        client_id (str): OAuth2 client ID.
        client_secret (str): OAuth2 client secret.
        customer_id (str): Zscaler tenant customer ID.
        vanity_domain (str): Tenant vanity domain.
        action (str): One of: list, get, add, update, delete.
        group_id (int/str, optional): Required for get/update/delete.
        name (str, optional): Required for add/update.
        description (str, optional): Optional.
        ip_addresses (list[str] or JSON str, optional): Required for add/update.
        search (str, optional): Optional search filter for list.

    Returns:
        dict or list of dicts: Group(s) info depending on action.
    """
    # Normalize IPs
    if isinstance(ip_addresses, str):
        try:
            ip_addresses = json.loads(ip_addresses)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for ip_addresses: {e}")

    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )

    zia = client.zia.cloud_firewall

    if action == "list":
        query_params = {"search": search} if search else {}
        groups, _, err = zia.list_ip_source_groups(query_params=query_params)
        if err:
            raise Exception(f"Error listing IP Source Groups: {err}")
        return [g.as_dict() for g in groups]

    elif action == "get":
        if not group_id:
            raise ValueError("group_id is required for get action.")
        group, _, err = zia.get_ip_source_group(group_id)
        if err:
            raise Exception(f"Error retrieving IP Source Group {group_id}: {err}")
        return group.as_dict()

    elif action == "add":
        if not name or not ip_addresses:
            raise ValueError("Both name and ip_addresses are required for add.")
        group, _, err = zia.add_ip_source_group(
            name=name,
            description=description,
            ip_addresses=ip_addresses,
        )
        if err:
            raise Exception(f"Error adding IP Source Group: {err}")
        return group.as_dict()

    elif action == "update":
        if not group_id or not name or not ip_addresses:
            raise ValueError("group_id, name, and ip_addresses are required for update.")
        group, _, err = zia.update_ip_source_group(
            group_id=group_id,
            name=name,
            description=description,
            ip_addresses=ip_addresses,
        )
        if err:
            raise Exception(f"Error updating IP Source Group: {err}")
        return group.as_dict()

    elif action == "delete":
        if not group_id:
            raise ValueError("group_id is required for delete action.")
        _, _, err = zia.delete_ip_source_group(group_id)
        if err:
            raise Exception(f"Error deleting IP Source Group {group_id}: {err}")
        return f"Group {group_id} deleted successfully."

    else:
        raise ValueError(f"Unsupported action: {action}")
