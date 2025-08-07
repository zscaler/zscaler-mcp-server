from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zia_locations_manager(
    action: Annotated[
        Literal["list", "get", "create", "update", "delete"],
        Field(description="One of: list, get, create, update, delete."),
    ],
    location_id: Annotated[
        Optional[int],
        Field(description="Location ID for get, update, or delete operations."),
    ] = None,
    location: Annotated[
        Optional[Union[Dict[str, Any], str]],
        Field(
            description="Required for create/update. Dictionary or JSON string of the location configuration."
        ),
    ] = None,
    query_params: Annotated[
        Optional[Dict[str, Any]],
        Field(description="Optional query parameters for filtering results."),
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Union[Dict[str, Any], List[Dict[str, Any]], str]:
    """
    FastMCP tool to manage ZIA Locations.

    Supported actions:
    - **list**: Retrieve all configured locations, with optional filters (e.g., `search`, `xff_enabled`).
    - **get**: Retrieve a specific location by ID.
    - **create**: Add a new location. Supports static IP or VPN credential-based setup.
    - **update**: Modify an existing location by ID.
    - **delete**: Remove a location by ID.

    Location Creation Modes:
    1. 🛰️ Static IP-based:
       - Set `ipAddresses` in the payload.
       - If no IP is provided, prompt user to create one using the `zia_static_ips` tool.

    2. 🛡️ VPN Credential-based:
       - Requires both `ipAddresses` and `vpnCredentials` fields.
       - VPN credential objects can be created via the `zia_vpn_credentials` tool.

    Location Payload Fields (examples only — see SDK for full spec):
    - `name` (str): Name of the location.
    - `country` (str): Country (e.g., "CANADA").
    - `tz` (str): Timezone (e.g., "CANADA_AMERICA_VANCOUVER").
    - `ipAddresses` (list[str]): List of static IPs, CIDRs, or GRE tunnel addresses.
    - `vpnCredentials` (list[dict]): Associated VPN credentials with `id` and `type`.
    - `xffForwardEnabled`, `authRequired`, `aupEnabled`, `ofwEnabled`, etc.: Boolean policy flags.
    - `profile` (str): Tag such as "CORPORATE", "SERVER", or "Unassigned".
    - `description` (str): Optional notes.

    Returns:
        - On `list`: List of location dictionaries.
        - On `get`, `create`, `update`: A single location dictionary.
        - On `delete`: Confirmation string.

    Deletion behavior:
    - Associated resources must be deleted in the reverse order they were created.

    Examples:
        >>> zia_locations_manager(
        ...     cloud="beta",
        ...     client_id="abc",
        ...     client_secret="xyz",
        ...     customer_id="123",
        ...     vanity_domain="company",
        ...     action="create",
        ...     location={
        ...         "name": "MCPLocation01",
        ...         "country": "CANADA",
        ...         "tz": "CANADA_AMERICA_VANCOUVER",
        ...         "ipAddresses": ["121.234.54.119"],
        ...         "xffForwardEnabled": True,
        ...         "ofwEnabled": True,
        ...         "aupEnabled": True,
        ...         "cautionEnabled": True,
        ...         "aupTimeoutInDays": 30,
        ...         "profile": "CORPORATE",
        ...         "description": "Provisioned from MCP"
        ...     }
        ... )
    """
    import json

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    zia = client.zia
    locations_api = zia.locations

    if action == "list":
        result, _, err = locations_api.list_locations(query_params=query_params or {})
        if err:
            raise Exception(f"Failed to list locations: {err}")
        return [loc.as_dict() for loc in result or []]

    elif action == "get":
        if not location_id:
            raise ValueError("You must provide `location_id` to retrieve a location.")
        result, _, err = locations_api.get_location(location_id)
        if err:
            raise Exception(f"Failed to get location {location_id}: {err}")
        return result.as_dict()

    elif action in ("create", "update"):
        if not location:
            raise ValueError("You must provide a `location` dictionary or JSON string.")

        if isinstance(location, str):
            try:
                location = json.loads(location)
            except Exception as e:
                raise ValueError(f"Invalid JSON for location: {e}")

        if not location.get("ipAddresses") and not location.get("vpnCredentials"):
            raise ValueError(
                "Location creation requires either `ipAddresses` or `vpnCredentials`. "
                "If neither is provided, you may want to create a static IP using the `zia_static_ips` tool."
            )

        if action == "create":
            created, _, err = locations_api.add_location(**location)
            if err:
                raise Exception(f"Failed to create location: {err}")
            return created.as_dict()

        if action == "update":
            if not location_id:
                raise ValueError("You must provide `location_id` to update a location.")
            updated, _, err = locations_api.update_location(location_id, **location)
            if err:
                raise Exception(f"Failed to update location {location_id}: {err}")
            return updated.as_dict()

    elif action == "delete":
        if not location_id:
            raise ValueError("You must provide `location_id` to delete a location.")
        _, _, err = locations_api.delete_location(location_id)
        if err:
            raise Exception(f"Failed to delete location {location_id}: {err}")
        return f"Deleted location {location_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
