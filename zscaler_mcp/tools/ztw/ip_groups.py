import json
from typing import Annotated, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def ztw_ip_group_manager(
    action: Annotated[
        Literal["read", "read_lite", "create", "delete"],
        Field(description="Action to perform: list, list_lite, add, or delete."),
    ] = "read",
    group_id: Annotated[
        Optional[Union[int, str]],
        Field(description="Required for delete action."),
    ] = None,
    name: Annotated[
        Optional[str], Field(description="Group name (required for add).")
    ] = None,
    description: Annotated[
        Optional[str], Field(description="Group description (optional for add).")
    ] = None,
    ip_addresses: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description="List of IP addresses (required for add). Accepts JSON string or list."
        ),
    ] = None,
    search: Annotated[
        Optional[str],
        Field(description="Optional search string for filtering list results."),
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
) -> Union[dict, List[dict], str]:
    """
    Performs CRUD operations on ZTW IP Groups.

    Args:
        action (str): One of: list, list_lite, add, delete.
        group_id (int/str, optional): Required for delete.
        name (str, optional): Required for add.
        description (str, optional): Optional for add.
        ip_addresses (list[str] or JSON str, optional): Required for add.
        search (str, optional): Optional search filter for list operations.

    Returns:
        dict or list of dicts: Group(s) info depending on action.
    """
    # Normalize IPs
    if isinstance(ip_addresses, str):
        try:
            ip_addresses = json.loads(ip_addresses)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for ip_addresses: {e}")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    ztw = client.ztw.ip_groups

    if action == "read":
        query_params = {"search": search} if search else {}
        groups, _, err = ztw.list_ip_groups(query_params=query_params)
        if err:
            raise Exception(f"Error listing IP Groups: {err}")
        return [g.as_dict() for g in groups]

    elif action == "read_lite":
        query_params = {"search": search} if search else {}
        groups, _, err = ztw.list_ip_groups_lite(query_params=query_params)
        if err:
            raise Exception(f"Error listing IP Groups (lite): {err}")
        return [g.as_dict() for g in groups]

    elif action == "create":
        if not name or not ip_addresses:
            raise ValueError("Both name and ip_addresses are required for add.")
        group, _, err = ztw.add_ip_group(
            name=name,
            description=description,
            ip_addresses=ip_addresses,
        )
        if err:
            raise Exception(f"Error adding IP Group: {err}")
        return group.as_dict()

    elif action == "delete":
        if not group_id:
            raise ValueError("group_id is required for delete action.")
        _, _, err = ztw.delete_ip_group(group_id)
        if err:
            raise Exception(f"Error deleting IP Group {group_id}: {err}")
        return f"Group {group_id} deleted successfully."

    else:
        raise ValueError(f"Unsupported action: {action}")
