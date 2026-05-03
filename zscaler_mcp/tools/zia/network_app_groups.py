import json
from typing import Annotated, Dict, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zia_list_network_app_groups(
    search: Annotated[
        Optional[str], Field(description="Search string to filter list results.")
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection of results."),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict]:
    """List ZIA network application groups with optional filtering.

    Supports JMESPath client-side filtering via the query parameter.
    """
    client = get_zscaler_client(service=service)
    zia = client.zia.cloud_firewall

    query_params = {"search": search} if search else {}
    groups, _, err = zia.list_network_app_groups(query_params=query_params)
    if err:
        raise Exception(f"Failed to list network app groups: {err}")
    results = [g.as_dict() for g in groups]
    return apply_jmespath(results, query)


def zia_get_network_app_group(
    group_id: Annotated[
        Union[int, str], Field(description="Group ID for the network application group.")
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Get a specific ZIA network application group by ID."""
    if not group_id:
        raise ValueError("group_id is required")

    client = get_zscaler_client(service=service)
    zia = client.zia.cloud_firewall

    group, _, err = zia.get_network_app_group(group_id)
    if err:
        raise Exception(f"Failed to retrieve network app group {group_id}: {err}")
    return group.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================


def zia_create_network_app_group(
    name: Annotated[str, Field(description="Group name (required).")],
    network_applications: Annotated[
        Union[List[str], str], Field(description="List of network application IDs (required).")
    ],
    description: Annotated[
        Optional[str], Field(description="Group description (optional).")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Create a new ZIA network application group."""
    if not name or not network_applications:
        raise ValueError("name and network_applications are required")

    if isinstance(network_applications, str):
        try:
            network_applications = json.loads(network_applications)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for network_applications: {e}")

    client = get_zscaler_client(service=service)
    zia = client.zia.cloud_firewall

    group, _, err = zia.add_network_app_group(
        name=name, description=description, network_applications=network_applications
    )
    if err:
        raise Exception(f"Failed to add network app group: {err}")
    return group.as_dict()


def zia_update_network_app_group(
    group_id: Annotated[Union[int, str], Field(description="Group ID (required).")],
    name: Annotated[str, Field(description="Group name (required).")],
    network_applications: Annotated[
        Union[List[str], str], Field(description="List of network application IDs (required).")
    ],
    description: Annotated[
        Optional[str], Field(description="Group description (optional).")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """Update an existing ZIA network application group."""
    if not group_id or not name or not network_applications:
        raise ValueError("group_id, name, and network_applications are required for update")

    if isinstance(network_applications, str):
        try:
            network_applications = json.loads(network_applications)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for network_applications: {e}")

    client = get_zscaler_client(service=service)
    zia = client.zia.cloud_firewall

    group, _, err = zia.update_network_app_group(
        group_id=group_id,
        name=name,
        description=description,
        network_applications=network_applications,
    )
    if err:
        raise Exception(f"Failed to update network app group {group_id}: {err}")
    return group.as_dict()


def zia_delete_network_app_group(
    group_id: Annotated[Union[int, str], Field(description="Group ID (required).")],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}",
) -> str:
    """Delete a ZIA network application group."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs

    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)

    confirmation_check = check_confirmation("zia_delete_network_app_group", confirmed, {"group_id": str(group_id)})
    if confirmation_check:
        return confirmation_check

    if not group_id:
        raise ValueError("group_id is required for delete")

    client = get_zscaler_client(service=service)
    zia = client.zia.cloud_firewall

    _, _, err = zia.delete_network_app_group(group_id)
    if err:
        raise Exception(f"Failed to delete network app group {group_id}: {err}")
    return f"Group {group_id} deleted successfully"
