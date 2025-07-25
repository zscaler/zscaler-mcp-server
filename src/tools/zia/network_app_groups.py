from src.sdk.zscaler_client import get_zscaler_client
from src.zscaler_mcp import app
from typing import Annotated, Union, List, Optional, Literal
from pydantic import Field
import json


@app.tool(
    name="zia_network_app_group",
    description="Manages ZIA Network Application Groups.",
)
def zia_network_app_group_manager(
    action: Annotated[
        Literal["list", "get", "add", "update", "delete"],
        Field(description="Action to perform on the network application group.")
    ] = "list",
    group_id: Annotated[
        Optional[Union[int, str]],
        Field(description="Required for get, update, and delete actions.")
    ] = None,
    name: Annotated[
        Optional[str],
        Field(description="Group name (required for add and update).")
    ] = None,
    description: Annotated[
        Optional[str],
        Field(description="Group description (optional).")
    ] = None,
    network_applications: Annotated[
        Optional[Union[List[str], str]],
        Field(description="List of network application IDs (required for add and update).")
    ] = None,
    search: Annotated[
        Optional[str],
        Field(description="Search string to filter list results.")
    ] = None,
    use_legacy: Annotated[
        bool,
        Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[
        str,
        Field(description="The service to use.")
    ] = "zia",
) -> Union[dict, List[dict], str]:
    """
    Manages ZIA Network Application Groups.

    Returns:
        dict | list[dict] | str: Group object(s) or status message.
    """
    if isinstance(network_applications, str):
        try:
            network_applications = json.loads(network_applications)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for network_applications: {e}")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    zia = client.zia.cloud_firewall

    if action == "list":
        query_params = {"search": search} if search else {}
        groups, _, err = zia.list_network_app_groups(query_params=query_params)
        if err:
            raise Exception(f"Failed to list network app groups: {err}")
        return [g.as_dict() for g in groups]

    if action == "get":
        if not group_id:
            raise ValueError("group_id is required for get.")
        group, _, err = zia.get_network_app_group(group_id)
        if err:
            raise Exception(f"Failed to retrieve group {group_id}: {err}")
        return group.as_dict()

    if action == "add":
        if not name or not network_applications:
            raise ValueError("name and network_applications are required for add.")
        group, _, err = zia.add_network_app_group(
            name=name,
            description=description,
            network_applications=network_applications,
        )
        if err:
            raise Exception(f"Failed to add network app group: {err}")
        return group.as_dict()

    if action == "update":
        if not group_id or not name or not network_applications:
            raise ValueError("group_id, name, and network_applications are required for update.")
        group, _, err = zia.update_network_app_group(
            group_id=group_id,
            name=name,
            description=description,
            network_applications=network_applications,
        )
        if err:
            raise Exception(f"Failed to update group {group_id}: {err}")
        return group.as_dict()

    if action == "delete":
        if not group_id:
            raise ValueError("group_id is required for delete.")
        _, _, err = zia.delete_network_app_group(group_id)
        if err:
            raise Exception(f"Failed to delete group {group_id}: {err}")
        return f"Group {group_id} deleted successfully."

    raise ValueError(f"Invalid action: {action}")
