import json
from typing import Annotated, Any, Dict, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zia_list_locations(
    query_params: Annotated[
        Optional[Dict[str, Any]],
        Field(description="Optional query parameters for filtering (e.g., search, xff_enabled)."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection of results."),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict[str, Any]]:
    """List all ZIA locations with optional filtering.

    Supports JMESPath client-side filtering via the query parameter.
    """
    client = get_zscaler_client(service=service)
    locations_api = client.zia.locations

    result, _, err = locations_api.list_locations(query_params=query_params or {})
    if err:
        raise Exception(f"Failed to list locations: {err}")
    results = [loc.as_dict() for loc in result or []]
    return apply_jmespath(results, query)


def zia_get_location(
    location_id: Annotated[int, Field(description="Location ID.")],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict[str, Any]:
    """Get a specific ZIA location by ID."""
    if not location_id:
        raise ValueError("location_id is required")

    client = get_zscaler_client(service=service)
    locations_api = client.zia.locations

    result, _, err = locations_api.get_location(location_id)
    if err:
        raise Exception(f"Failed to get location {location_id}: {err}")
    return result.as_dict()


def zia_list_location_groups(
    search: Annotated[
        Optional[str],
        Field(
            description=(
                "Server-side substring search across location group attributes "
                "(forwarded to ZIA's ``search`` query parameter)."
            )
        ),
    ] = None,
    name: Annotated[
        Optional[str],
        Field(description="Filter by exact location group name (forwarded to ZIA's ``name`` query parameter)."),
    ] = None,
    group_type: Annotated[
        Optional[str],
        Field(
            description=(
                "Filter by group type. ZIA supports ``Static`` (manually-curated "
                "membership) and ``Dynamic`` (membership driven by location attributes)."
            )
        ),
    ] = None,
    location_id: Annotated[
        Optional[int],
        Field(description="Return only location groups that include this location ID."),
    ] = None,
    page: Annotated[Optional[int], Field(description="Page offset for pagination.")] = None,
    page_size: Annotated[
        Optional[int],
        Field(description="Page size. Default 100; maximum 1000."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection."),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Any:
    """List ZIA location groups, used as the ``location_groups`` operand on rule resources.

    Location groups are referenced by ID on every ZIA rule resource that
    accepts a ``location_groups`` field (Cloud Firewall, DNS, IPS, URL
    Filtering, SSL Inspection, Web DLP, File Type Control, Sandbox,
    Cloud App Control). The ZIA API does not expose a create/update/delete
    operation for location groups via the public endpoint — this tool is
    read-only.

    Supports JMESPath client-side filtering via the ``query`` parameter.
    """
    query_params: Dict[str, Any] = {}
    if search is not None:
        query_params["search"] = search
    if name is not None:
        query_params["name"] = name
    if group_type is not None:
        query_params["group_type"] = group_type
    if location_id is not None:
        query_params["location_id"] = location_id
    if page is not None:
        query_params["page"] = page
    if page_size is not None:
        query_params["page_size"] = page_size

    client = get_zscaler_client(service=service)
    locations_api = client.zia.locations

    result, _, err = locations_api.list_location_groups(query_params=query_params or None)
    if err:
        raise Exception(f"Failed to list location groups: {err}")
    results = [grp.as_dict() for grp in result or []]
    return apply_jmespath(results, query)


def zia_get_location_group(
    group_id: Annotated[int, Field(description="Location group ID.")],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict[str, Any]:
    """Get a specific ZIA location group by ID."""
    if not group_id:
        raise ValueError("group_id is required")

    client = get_zscaler_client(service=service)
    locations_api = client.zia.locations

    result, _, err = locations_api.get_location_group(group_id)
    if err:
        raise Exception(f"Failed to get location group {group_id}: {err}")
    return result.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================


def zia_create_location(
    location: Annotated[
        Union[Dict[str, Any], str],
        Field(description="Location configuration as dictionary or JSON string (required)."),
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict[str, Any]:
    """
    Create a new ZIA location.

    Location Creation Modes:
    1. Static IP-based: Set `ipAddresses` in the payload.
    2. VPN Credential-based: Requires both `ipAddresses` and `vpnCredentials` fields.

    Required fields typically include:
    - name (str): Name of the location
    - country (str): Country (e.g., "CANADA")
    - tz (str): Timezone (e.g., "CANADA_AMERICA_VANCOUVER")
    - ipAddresses (list[str]): List of static IPs, CIDRs, or GRE tunnel addresses

    Optional fields include:
    - vpnCredentials (list[dict]): Associated VPN credentials with `id` and `type`
    - xffForwardEnabled, authRequired, aupEnabled, ofwEnabled, etc.: Boolean policy flags
    - profile (str): Tag such as "CORPORATE", "SERVER", or "Unassigned"
    - description (str): Optional notes
    """
    if not location:
        raise ValueError("location dictionary or JSON string is required")

    if isinstance(location, str):
        try:
            location = json.loads(location)
        except Exception as e:
            raise ValueError(f"Invalid JSON for location: {e}")

    if not location.get("ipAddresses") and not location.get("vpnCredentials"):
        raise ValueError(
            "Location creation requires either `ipAddresses` or `vpnCredentials`. "
            "If neither is provided, you may want to create a static IP using the `zia_create_static_ip` tool."
        )

    client = get_zscaler_client(service=service)
    locations_api = client.zia.locations

    created, _, err = locations_api.add_location(**location)
    if err:
        raise Exception(f"Failed to create location: {err}")
    return created.as_dict()


def zia_update_location(
    location_id: Annotated[int, Field(description="Location ID (required).")],
    location: Annotated[
        Union[Dict[str, Any], str],
        Field(
            description="Updated location configuration as dictionary or JSON string (required)."
        ),
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict[str, Any]:
    """Update an existing ZIA location."""
    if not location_id or not location:
        raise ValueError("location_id and location configuration are required")

    if isinstance(location, str):
        try:
            location = json.loads(location)
        except Exception as e:
            raise ValueError(f"Invalid JSON for location: {e}")

    client = get_zscaler_client(service=service)
    locations_api = client.zia.locations

    updated, _, err = locations_api.update_location(location_id, **location)
    if err:
        raise Exception(f"Failed to update location {location_id}: {err}")
    return updated.as_dict()


def zia_delete_location(
    location_id: Annotated[int, Field(description="Location ID (required).")],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}",
) -> str:
    """
    Delete a ZIA location.

    Note: Associated resources must be deleted in the reverse order they were created.
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs

    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)

    confirmation_check = check_confirmation("zia_delete_location", confirmed, {"location_id": str(location_id)})
    if confirmation_check:
        return confirmation_check

    if not location_id:
        raise ValueError("location_id is required")

    client = get_zscaler_client(service=service)
    locations_api = client.zia.locations

    _, _, err = locations_api.delete_location(location_id)
    if err:
        raise Exception(f"Failed to delete location {location_id}: {err}")
    return f"Deleted location {location_id}"
