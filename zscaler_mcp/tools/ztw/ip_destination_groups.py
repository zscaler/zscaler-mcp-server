import json
from typing import Annotated, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.utils.utils import validate_and_convert_country_codes


def ztw_ip_destination_group_manager(
    action: Annotated[
        Literal["list", "list_lite", "add", "delete"],
        Field(description="Action to perform on IP destination groups."),
    ] = "list",
    group_id: Annotated[
        Optional[Union[int, str]],
        Field(description="Required for delete action."),
    ] = None,
    name: Annotated[
        Optional[str],
        Field(description="Name of the destination group (required for add)."),
    ] = None,
    description: Annotated[
        Optional[str], Field(description="Description of the group (optional).")
    ] = None,
    type: Annotated[
        Optional[str],
        Field(
            description="Group type (DSTN_IP, DSTN_FQDN, DSTN_DOMAIN, DSTN_OTHER). Required for add."
        ),
    ] = None,
    addresses: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description="List of IPs/FQDNs. Required for add if type is DSTN_IP or DSTN_FQDN."
        ),
    ] = None,
    countries: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description="List of countries (e.g., 'Canada', 'US', 'COUNTRY_CA', 'CA'). Will be converted to COUNTRY_XX format. Only supported when type is DSTN_OTHER."
        ),
    ] = None,
    exclude_type: Annotated[
        Optional[str],
        Field(
            description="Optional filter for list. Exclude groups of type DSTN_IP, DSTN_FQDN, etc."
        ),
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
) -> Union[dict, List[dict], str]:
    """
    Manages ZTW IP Destination Groups.

    Returns:
        dict | list[dict] | str: Group object(s) or status message.
    """

    # Normalize list fields
    def parse_list(val):
        if isinstance(val, str):
            return json.loads(val)
        return val

    addresses = parse_list(addresses)
    
    # Validate and convert country codes to Zscaler format
    if countries:
        try:
            countries = validate_and_convert_country_codes(countries)
        except ValueError as e:
            raise ValueError(f"Invalid country code: {e}")
        
        # Validate that countries are only used with DSTN_OTHER type
        if type and type != "DSTN_OTHER":
            raise ValueError("Countries are only supported when type is DSTN_OTHER")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    ztw = client.ztw.ip_destination_groups

    if action == "list":
        query_params = {"exclude_type": exclude_type} if exclude_type else {}
        groups, _, err = ztw.list_ip_destination_groups(query_params=query_params)
        if err:
            raise Exception(f"Failed to list destination groups: {err}")
        return [g.as_dict() for g in groups]

    elif action == "list_lite":
        query_params = {"exclude_type": exclude_type} if exclude_type else {}
        groups, _, err = ztw.list_ip_destination_groups_lite(query_params=query_params)
        if err:
            raise Exception(f"Failed to list destination groups (lite): {err}")
        return [g.as_dict() for g in groups]

    elif action == "add":
        if not name or not type:
            raise ValueError("name and type are required for add.")
        group, _, err = ztw.add_ip_destination_group(
            name=name,
            description=description,
            type=type,
            addresses=addresses,
            countries=countries,
        )
        if err:
            raise Exception(f"Failed to add group: {err}")
        return group.as_dict()

    elif action == "delete":
        if not group_id:
            raise ValueError("group_id is required for delete.")
        _, _, err = ztw.delete_ip_destination_group(group_id)
        if err:
            raise Exception(f"Failed to delete group {group_id}: {err}")
        return f"Group {group_id} deleted successfully."

    raise ValueError(f"Invalid action: {action}")
