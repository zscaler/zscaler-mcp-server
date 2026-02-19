"""
ZIA Network Service Groups MCP Tools.

This module provides MCP tools for managing ZIA Network Service Groups, which
allow you to group multiple network services together for use in Cloud Firewall policies.

Network Service Groups enable you to:
- Organize related network services into logical groups
- Simplify firewall rule management by referencing groups instead of individual services
- Apply consistent policies across multiple services
- Reduce rule complexity and improve maintainability

Dependencies:
    - Requires valid Zscaler credentials (ZSCALER_CLIENT_ID, ZSCALER_CLIENT_SECRET, ZSCALER_VANITY_DOMAIN)
    - Uses the zscaler-sdk-python cloud_firewall module

Related Tools:
    - zia_list_network_services: List individual network services to get their IDs
    - zia_get_network_service: Get details of a specific network service
    - zia_create_network_service: Create custom network services before grouping them
    - zia_list_cloud_firewall_rules: Use network service groups in firewall policies

Example Usage:
    # List all network service groups
    groups = zia_list_network_svc_groups()

    # Get a specific group
    group = zia_get_network_svc_group(group_id="12345")

    # Create a new group with services
    new_group = zia_create_network_svc_group(
        name="Web Services",
        description="HTTP and HTTPS services",
        service_ids='["159143", "159144"]'
    )

    # Update a group
    updated = zia_update_network_svc_group(
        group_id="12345",
        name="Updated Web Services",
        service_ids='["159143", "159144", "159145"]'
    )

    # Delete a group
    result = zia_delete_network_svc_group(group_id="12345")
"""

import json
from typing import Annotated, Dict, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zia_list_network_svc_groups(
    search: Annotated[
        Optional[str],
        Field(description="Search string to filter by group name or description.")
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[Dict]:
    """
    List ZIA network service groups with optional filtering.

    Network service groups organize multiple network services into logical
    collections that can be referenced in Cloud Firewall policies.

    Args:
        search: Filter results by name or description substring match.
        use_legacy: Whether to use legacy API (default: False).
        service: The service identifier (default: "zia").

    Returns:
        List of network service group dictionaries containing:
        - id: Unique identifier for the group
        - name: Name of the network service group
        - description: Description of the group
        - services: List of network services in the group (with id, name, etc.)

    Examples:
        >>> # List all network service groups
        >>> groups = zia_list_network_svc_groups()

        >>> # Search for groups containing "web" in name or description
        >>> web_groups = zia_list_network_svc_groups(search="web")

        >>> # Search for email-related service groups
        >>> email_groups = zia_list_network_svc_groups(search="email")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall

    query_params = {}
    if search:
        query_params["search"] = search

    groups, _, err = zia.list_network_svc_groups(query_params=query_params if query_params else None)
    if err:
        raise Exception(f"Failed to list network service groups: {err}")
    return [g.as_dict() for g in groups]


def zia_get_network_svc_group(
    group_id: Annotated[
        Union[int, str],
        Field(description="The unique ID of the network service group to retrieve.")
    ],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """
    Get a specific ZIA network service group by ID.

    Retrieves detailed information about a single network service group including
    all associated network services.

    Args:
        group_id: The unique identifier of the network service group.
        use_legacy: Whether to use legacy API (default: False).
        service: The service identifier (default: "zia").

    Returns:
        Dictionary containing the network service group details:
        - id: Unique identifier
        - name: Group name
        - description: Group description
        - services: List of network services in the group, each containing:
            - id: Service ID
            - name: Service name
            - description: Service description
            - type: Service type

    Examples:
        >>> group = zia_get_network_svc_group(group_id="12345")
        >>> print(f"Group: {group['name']}")
        >>> print(f"Services count: {len(group.get('services', []))}")

        >>> # Get group and list its services
        >>> group = zia_get_network_svc_group(group_id="67890")
        >>> for svc in group.get('services', []):
        ...     print(f"  - {svc['name']} (ID: {svc['id']})")
    """
    if not group_id:
        raise ValueError("group_id is required")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall

    group, _, err = zia.get_network_svc_group(group_id)
    if err:
        raise Exception(f"Failed to retrieve network service group {group_id}: {err}")
    return group.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================


def _parse_service_ids(service_ids_input: Union[List, str, None]) -> Optional[List]:
    """
    Parse service IDs input which can be a list or JSON string.

    Args:
        service_ids_input: List of service IDs or JSON string representation.

    Returns:
        Parsed list of service IDs or None if input is empty.

    Raises:
        ValueError: If JSON parsing fails or format is invalid.
    """
    if service_ids_input is None:
        return None

    if isinstance(service_ids_input, str):
        try:
            service_ids_input = json.loads(service_ids_input)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for service_ids: {e}")

    if not isinstance(service_ids_input, list):
        raise ValueError("service_ids must be a list of network service IDs")

    # Convert all elements to strings (the SDK expects string IDs)
    return [str(sid) for sid in service_ids_input]


def zia_create_network_svc_group(
    name: Annotated[str, Field(description="Name for the network service group (required).")],
    service_ids: Annotated[
        Union[List, str],
        Field(
            description="""List of network service IDs to include in the group.
            Can be provided as a JSON array string or Python list.
            Examples:
            - JSON: '["159143", "159144", "159145"]'
            - List: ["159143", "159144"]
            Use zia_list_network_services to find available service IDs."""
        )
    ],
    description: Annotated[
        Optional[str],
        Field(description="Description for the network service group (optional).")
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """
    Create a new ZIA network service group.

    Network service groups bundle multiple network services together for easier
    management in Cloud Firewall policies. Instead of specifying individual
    services in firewall rules, you can reference a group.

    Args:
        name: Name for the new network service group (required).
        service_ids: List of network service IDs to include in the group.
            Use zia_list_network_services() to get available service IDs.
        description: Optional description for the group.
        use_legacy: Whether to use legacy API (default: False).
        service: The service identifier (default: "zia").

    Returns:
        Dictionary containing the created network service group with all fields.

    Raises:
        ValueError: If required parameters are missing or format is invalid.
        Exception: If the API call fails.

    Examples:
        >>> # Create a group for web services
        >>> web_group = zia_create_network_svc_group(
        ...     name="Web Services",
        ...     description="HTTP and HTTPS services",
        ...     service_ids='["159143", "159144"]'
        ... )

        >>> # Create a group for database services
        >>> db_group = zia_create_network_svc_group(
        ...     name="Database Services",
        ...     description="Common database ports",
        ...     service_ids='["159150", "159151", "159152"]'
        ... )

        >>> # Create with Python list
        >>> mail_group = zia_create_network_svc_group(
        ...     name="Email Services",
        ...     description="SMTP, IMAP, POP3",
        ...     service_ids=["159160", "159161", "159162"]
        ... )

    Workflow:
        1. First, list available services: zia_list_network_services()
        2. Note the IDs of services you want to group
        3. Create the group with those IDs
        4. Reference the group in firewall rules
    """
    if not name:
        raise ValueError("name is required")
    if not service_ids:
        raise ValueError("service_ids is required - must specify at least one network service ID")

    parsed_service_ids = _parse_service_ids(service_ids)
    if not parsed_service_ids:
        raise ValueError("service_ids must contain at least one network service ID")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall

    kwargs = {"name": name, "service_ids": parsed_service_ids}
    if description:
        kwargs["description"] = description

    group, _, err = zia.add_network_svc_group(**kwargs)
    if err:
        raise Exception(f"Failed to create network service group: {err}")
    return group.as_dict()


def zia_update_network_svc_group(
    group_id: Annotated[
        Union[int, str],
        Field(description="The unique ID of the network service group to update (required).")
    ],
    name: Annotated[
        str,
        Field(description="Updated name for the network service group (required for update).")
    ],
    service_ids: Annotated[
        Optional[Union[List, str]],
        Field(
            description="""Updated list of network service IDs. If provided, REPLACES existing services.
            Can be provided as a JSON array string or Python list.
            Examples:
            - JSON: '["159143", "159144", "159145"]'
            - List: ["159143", "159144"]
            If omitted, existing services are preserved."""
        )
    ] = None,
    description: Annotated[
        Optional[str],
        Field(description="Updated description (optional).")
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict:
    """
    Update an existing ZIA network service group.

    Updates the specified network service group. If service_ids are provided,
    they will REPLACE the existing services in the group. If service_ids are
    not provided, the existing services will be preserved.

    Args:
        group_id: The unique ID of the network service group to update (required).
        name: Updated name for the group (required).
        service_ids: Optional updated list of service IDs. If provided, replaces all existing services.
        description: Optional updated description.
        use_legacy: Whether to use legacy API (default: False).
        service: The service identifier (default: "zia").

    Returns:
        Dictionary containing the updated network service group.

    Raises:
        ValueError: If required parameters are missing or format is invalid.
        Exception: If the API call fails.

    Examples:
        >>> # Update group name and description (keep existing services)
        >>> updated = zia_update_network_svc_group(
        ...     group_id="12345",
        ...     name="Renamed Web Services",
        ...     description="Updated description"
        ... )

        >>> # Update services in the group (replaces existing)
        >>> updated = zia_update_network_svc_group(
        ...     group_id="12345",
        ...     name="Web Services",
        ...     service_ids='["159143", "159144", "159146"]'
        ... )

        >>> # Add more services to a group
        >>> # First, get existing services
        >>> group = zia_get_network_svc_group(group_id="12345")
        >>> existing_ids = [str(s['id']) for s in group.get('services', [])]
        >>> new_ids = existing_ids + ["159147"]
        >>> updated = zia_update_network_svc_group(
        ...     group_id="12345",
        ...     name=group['name'],
        ...     service_ids=new_ids
        ... )
    """
    if not group_id:
        raise ValueError("group_id is required")
    if not name:
        raise ValueError("name is required for update")

    parsed_service_ids = _parse_service_ids(service_ids) if service_ids else None

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall

    kwargs = {"name": name}
    if parsed_service_ids is not None:
        kwargs["service_ids"] = parsed_service_ids
    if description is not None:
        kwargs["description"] = description

    group, _, err = zia.update_network_svc_group(group_id=int(group_id), **kwargs)
    if err:
        raise Exception(f"Failed to update network service group {group_id}: {err}")
    return group.as_dict()


def zia_delete_network_svc_group(
    group_id: Annotated[
        Union[int, str],
        Field(description="The unique ID of the network service group to delete (required).")
    ],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}"
) -> str:
    """
    Delete a ZIA network service group.

    Permanently deletes the specified network service group. This action cannot
    be undone. The group must not be in use by any firewall rules before deletion.

    Note: Deleting a group does NOT delete the individual network services
    contained within it - only the grouping is removed.

    Args:
        group_id: The unique ID of the network service group to delete (required).
        use_legacy: Whether to use legacy API (default: False).
        service: The service identifier (default: "zia").
        kwargs: JSON string for internal confirmation handling.

    Returns:
        Success message confirming deletion.

    Raises:
        ValueError: If group_id is not provided.
        Exception: If the API call fails (e.g., group in use, not found).

    Examples:
        >>> # Delete a network service group
        >>> result = zia_delete_network_svc_group(group_id="12345")
        >>> print(result)  # "Network service group 12345 deleted successfully"

    Warning:
        - Ensure the group is not referenced by any firewall rules
        - This operation cannot be undone
        - The individual services in the group are NOT deleted
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs

    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)

    confirmation_check = check_confirmation(
        "zia_delete_network_svc_group",
        confirmed,
        {}
    )
    if confirmation_check:
        return confirmation_check

    if not group_id:
        raise ValueError("group_id is required for delete")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    zia = client.zia.cloud_firewall

    _, _, err = zia.delete_network_svc_group(group_id)
    if err:
        raise Exception(f"Failed to delete network service group {group_id}: {err}")
    return f"Network service group {group_id} deleted successfully"
