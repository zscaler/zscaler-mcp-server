from zscaler_mcp.sdk.zscaler_client import get_zscaler_client
from zscaler_mcp import app
from typing import Annotated, Union, List, Optional, Literal
from pydantic import Field
import json


@app.tool(
    name="zia_ip_destination_groups",
    description="Manages ZIA IP Destination Groups.",
)
def zia_ip_destination_group_manager(
    action: Annotated[
        Literal["list", "get", "add", "update", "delete"],
        Field(description="Action to perform on IP destination groups.")
    ] = "list",
    group_id: Annotated[
        Optional[Union[int, str]],
        Field(description="Required for get, update, and delete actions.")
    ] = None,
    name: Annotated[
        Optional[str],
        Field(description="Name of the destination group (required for add/update).")
    ] = None,
    description: Annotated[
        Optional[str],
        Field(description="Description of the group (optional).")
    ] = None,
    type: Annotated[
        Optional[str],
        Field(description="Group type (DSTN_IP, DSTN_FQDN, DSTN_DOMAIN, DSTN_OTHER). Required for add/update.")
    ] = None,
    addresses: Annotated[
        Optional[Union[List[str], str]],
        Field(description="List of IPs/FQDNs. Required for add/update if type is DSTN_IP or DSTN_FQDN.")
    ] = None,
    countries: Annotated[
        Optional[Union[List[str], str]],
        Field(description="List of country codes (e.g., COUNTRY_CA). Optional for DSTN_OTHER.")
    ] = None,
    ip_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(description="List of URL categories (e.g., CUSTOM_01). Optional for DSTN_OTHER.")
    ] = None,
    exclude_type: Annotated[
        Optional[str],
        Field(description="Optional filter for list. Exclude groups of type DSTN_IP, DSTN_FQDN, etc.")
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
    Manages ZIA IP Destination Groups.

    Returns:
        dict | list[dict] | str: Group object(s) or status message.
    """
    # Normalize list fields
    def parse_list(val):
        if isinstance(val, str):
            return json.loads(val)
        return val

    addresses = parse_list(addresses)
    countries = parse_list(countries)
    ip_categories = parse_list(ip_categories)

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    zia = client.zia.cloud_firewall

    if action == "list":
        query_params = {"exclude_type": exclude_type} if exclude_type else {}
        groups, _, err = zia.list_ip_destination_groups(query_params=query_params)
        if err:
            raise Exception(f"Failed to list destination groups: {err}")
        return [g.as_dict() for g in groups]

    if action == "get":
        if not group_id:
            raise ValueError("group_id is required for get.")
        group, _, err = zia.get_ip_destination_group(group_id)
        if err:
            raise Exception(f"Failed to retrieve group {group_id}: {err}")
        return group.as_dict()

    if action == "add":
        if not name or not type:
            raise ValueError("name and type are required for add.")
        group, _, err = zia.add_ip_destination_group(
            name=name,
            description=description,
            type=type,
            addresses=addresses,
            countries=countries,
            ip_categories=ip_categories,
        )
        if err:
            raise Exception(f"Failed to add group: {err}")
        return group.as_dict()

    if action == "update":
        if not group_id or not name or not type:
            raise ValueError("group_id, name, and type are required for update.")
        group, _, err = zia.update_ip_destination_group(
            group_id=group_id,
            name=name,
            description=description,
            type=type,
            addresses=addresses,
            countries=countries,
            ip_categories=ip_categories,
        )
        if err:
            raise Exception(f"Failed to update group {group_id}: {err}")
        return group.as_dict()

    if action == "delete":
        if not group_id:
            raise ValueError("group_id is required for delete.")
        _, _, err = zia.delete_ip_destination_group(group_id)
        if err:
            raise Exception(f"Failed to delete group {group_id}: {err}")
        return f"Group {group_id} deleted successfully."

    raise ValueError(f"Invalid action: {action}")
