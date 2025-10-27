import json
from typing import Annotated, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# ============================================================================
# Helper Functions
# ============================================================================

def _parse_list(val):
    """Helper function to parse list parameters that can be JSON strings or lists."""
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {e}")
    return val


def _build_firewall_rule_payload(
    name: Optional[str] = None,
    description: Optional[str] = None,
    rule_action: Optional[str] = None,
    enabled: Optional[bool] = None,
    rank: Optional[int] = None,
    order: Optional[int] = None,
    src_ips: Optional[Union[List[str], str]] = None,
    dest_addresses: Optional[Union[List[str], str]] = None,
    source_countries: Optional[Union[List[str], str]] = None,
    dest_countries: Optional[Union[List[str], str]] = None,
    exclude_src_countries: Optional[bool] = None,
    dest_ip_categories: Optional[Union[List[str], str]] = None,
    device_trust_levels: Optional[Union[List[str], str]] = None,
    nw_applications: Optional[Union[List[str], str]] = None,
    enable_full_logging: Optional[bool] = None,
    predefined: Optional[bool] = None,
    default_rule: Optional[bool] = None,
    app_services: Optional[Union[List[int], str]] = None,
    app_service_groups: Optional[Union[List[int], str]] = None,
    departments: Optional[Union[List[int], str]] = None,
    dest_ip_groups: Optional[Union[List[int], str]] = None,
    dest_ipv6_groups: Optional[Union[List[int], str]] = None,
    devices: Optional[Union[List[int], str]] = None,
    device_groups: Optional[Union[List[int], str]] = None,
    groups: Optional[Union[List[int], str]] = None,
    labels: Optional[Union[List[int], str]] = None,
    locations: Optional[Union[List[int], str]] = None,
    location_groups: Optional[Union[List[int], str]] = None,
    nw_application_groups: Optional[Union[List[int], str]] = None,
    nw_services: Optional[Union[List[int], str]] = None,
    nw_service_groups: Optional[Union[List[int], str]] = None,
    time_windows: Optional[Union[List[int], str]] = None,
    users: Optional[Union[List[int], str]] = None,
) -> dict:
    """Build payload for firewall rule operations."""
    payload = {}

    # Core parameters
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if rule_action is not None:
        payload["action"] = rule_action
    if enabled is not None:
        payload["enabled"] = enabled
    if rank is not None:
        payload["rank"] = rank
    if order is not None:
        payload["order"] = order

    # List parameters that need parsing
    for param_name, param_value in [
        ("src_ips", src_ips),
        ("dest_addresses", dest_addresses),
        ("source_countries", source_countries),
        ("dest_countries", dest_countries),
        ("dest_ip_categories", dest_ip_categories),
        ("device_trust_levels", device_trust_levels),
        ("nw_applications", nw_applications),
        ("app_services", app_services),
        ("app_service_groups", app_service_groups),
        ("departments", departments),
        ("dest_ip_groups", dest_ip_groups),
        ("dest_ipv6_groups", dest_ipv6_groups),
        ("devices", devices),
        ("device_groups", device_groups),
        ("groups", groups),
        ("labels", labels),
        ("locations", locations),
        ("location_groups", location_groups),
        ("nw_application_groups", nw_application_groups),
        ("nw_services", nw_services),
        ("nw_service_groups", nw_service_groups),
        ("time_windows", time_windows),
        ("users", users),
    ]:
        if param_value is not None:
            payload[param_name] = _parse_list(param_value)

    # Boolean parameters
    if exclude_src_countries is not None:
        payload["exclude_src_countries"] = exclude_src_countries
    if enable_full_logging is not None:
        payload["enable_full_logging"] = enable_full_logging
    if predefined is not None:
        payload["predefined"] = predefined
    if default_rule is not None:
        payload["default_rule"] = default_rule

    return payload


# ============================================================================
# READ OPERATIONS (Read-Only)
# ============================================================================

def zia_list_cloud_firewall_rules(
    search: Annotated[
        Optional[str], Field(description="Optional search filter for listing rules by name.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[dict]:
    """
    Lists all ZIA Cloud Firewall Rules with optional search filtering.
    This is a read-only operation.

    Cloud Firewall Rules control network traffic based on source/destination IPs, countries,
    network applications, device trust levels, and other attributes.

    Args:
        search (str, optional): Search string for filtering rules by name.
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "zia").

    Returns:
        list[dict]: List of cloud firewall rule objects.

    Example:
        List all rules:
        >>> rules = zia_list_cloud_firewall_rules()

        Search for rules containing "block":
        >>> rules = zia_list_cloud_firewall_rules(search="block")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    fw = client.zia.cloud_firewall_rules

    query = {"search": search} if search else {}
    rules, _, err = fw.list_rules(query_params=query)
    if err:
        raise Exception(f"Failed to list cloud firewall rules: {err}")
    return [r.as_dict() for r in rules]


def zia_get_cloud_firewall_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the cloud firewall rule to retrieve.")
    ],
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Gets a specific ZIA Cloud Firewall Rule by ID.
    This is a read-only operation.

    Args:
        rule_id (int/str): The ID of the cloud firewall rule to retrieve.
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "zia").

    Returns:
        dict: The cloud firewall rule object.

    Example:
        Get a specific rule:
        >>> rule = zia_get_cloud_firewall_rule(rule_id="12345")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    fw = client.zia.cloud_firewall_rules

    rule, _, err = fw.get_rule(rule_id)
    if err:
        raise Exception(f"Failed to retrieve rule {rule_id}: {err}")
    return rule.as_dict()


# ============================================================================
# WRITE OPERATIONS (Require --enable-write-tools flag)
# ============================================================================

def zia_create_cloud_firewall_rule(
    name: Annotated[str, Field(description="Rule name (required).")],
    rule_action: Annotated[
        str, Field(description="Action for the rule. Values: ALLOW, BLOCK, BYPASS, INSPECT")
    ],
    description: Annotated[
        Optional[str], Field(description="Optional rule description.")
    ] = None,
    enabled: Annotated[
        Optional[bool], Field(description="True to enable rule, False to disable.")
    ] = True,
    rank: Annotated[
        Optional[int], Field(description="Admin rank of the rule.")
    ] = None,
    order: Annotated[
        Optional[int], Field(description="Rule order, defaults to the bottom.")
    ] = None,
    src_ips: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Source IPs for the rule. Accepts IP addresses or CIDR. Accepts JSON string or list.")
    ] = None,
    dest_addresses: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Destination IPs for the rule. Accepts IP addresses, CIDR, or hostnames. Accepts JSON string or list.")
    ] = None,
    source_countries: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Source countries for the rule. Accepts JSON string or list.")
    ] = None,
    dest_countries: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Destination countries for the rule. Accepts JSON string or list.")
    ] = None,
    exclude_src_countries: Annotated[
        Optional[bool], Field(description="Exclude source countries from the rule.")
    ] = None,
    dest_ip_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(description="IP address categories for the rule. Accepts JSON string or list.")
    ] = None,
    device_trust_levels: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Device trust levels for the rule application. Values: ANY, UNKNOWN_DEVICETRUSTLEVEL, LOW_TRUST, MEDIUM_TRUST, HIGH_TRUST")
    ] = None,
    nw_applications: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Network service applications for the rule. Accepts JSON string or list.")
    ] = None,
    enable_full_logging: Annotated[
        Optional[bool], Field(description="If True, enables full logging.")
    ] = None,
    predefined: Annotated[
        Optional[bool], Field(description="Indicates that the rule is predefined by using a true value.")
    ] = None,
    default_rule: Annotated[
        Optional[bool], Field(description="Indicates whether the rule is the Default Cloud IPS Rule or not.")
    ] = None,
    app_services: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for application services for the rule.")
    ] = None,
    app_service_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for app service groups.")
    ] = None,
    departments: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for departments the rule applies to.")
    ] = None,
    dest_ip_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for destination IP groups.")
    ] = None,
    dest_ipv6_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for destination IPV6 groups.")
    ] = None,
    devices: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for devices managed by Zscaler Client Connector.")
    ] = None,
    device_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for device groups managed by Zscaler Client Connector.")
    ] = None,
    groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for groups the rule applies to.")
    ] = None,
    labels: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for labels the rule applies to.")
    ] = None,
    locations: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for locations the rule applies to.")
    ] = None,
    location_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for location groups.")
    ] = None,
    nw_application_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for network application groups.")
    ] = None,
    nw_services: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for network services the rule applies to.")
    ] = None,
    nw_service_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for network service groups.")
    ] = None,
    time_windows: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for time windows the rule applies to.")
    ] = None,
    users: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for users the rule applies to.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Creates a new ZIA Cloud Firewall Rule.
    This is a write operation that requires the --enable-write-tools flag.

    Args:
        name (str): Rule name (required).
        rule_action (str): Action for the rule. Values: ALLOW, BLOCK, BYPASS, INSPECT.
        description (str, optional): Optional rule description.
        enabled (bool, optional): True to enable rule, False to disable (default: True).
        rank (int, optional): Admin rank of the rule.
        order (int, optional): Rule order, defaults to the bottom.
        [... additional parameters as documented in function signature ...]

    Returns:
        dict: The created cloud firewall rule object.

    Example:
        Create a rule to allow traffic to Google DNS:
        >>> rule = zia_create_cloud_firewall_rule(
        ...     name="Allow Google DNS",
        ...     rule_action="ALLOW",
        ...     src_ips=["192.168.100.0/24"],
        ...     dest_addresses=["8.8.8.8", "8.8.4.4"],
        ...     enable_full_logging=True
        ... )
    """
    payload = _build_firewall_rule_payload(
        name=name,
        description=description,
        rule_action=rule_action,
        enabled=enabled,
        rank=rank,
        order=order,
        src_ips=src_ips,
        dest_addresses=dest_addresses,
        source_countries=source_countries,
        dest_countries=dest_countries,
        exclude_src_countries=exclude_src_countries,
        dest_ip_categories=dest_ip_categories,
        device_trust_levels=device_trust_levels,
        nw_applications=nw_applications,
        enable_full_logging=enable_full_logging,
        predefined=predefined,
        default_rule=default_rule,
        app_services=app_services,
        app_service_groups=app_service_groups,
        departments=departments,
        dest_ip_groups=dest_ip_groups,
        dest_ipv6_groups=dest_ipv6_groups,
        devices=devices,
        device_groups=device_groups,
        groups=groups,
        labels=labels,
        locations=locations,
        location_groups=location_groups,
        nw_application_groups=nw_application_groups,
        nw_services=nw_services,
        nw_service_groups=nw_service_groups,
        time_windows=time_windows,
        users=users,
    )

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    fw = client.zia.cloud_firewall_rules

    rule, _, err = fw.add_rule(**payload)
    if err:
        raise Exception(f"Failed to add cloud firewall rule: {err}")
    return rule.as_dict()


def zia_update_cloud_firewall_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the cloud firewall rule to update.")
    ],
    name: Annotated[
        Optional[str], Field(description="Rule name.")
    ] = None,
    description: Annotated[
        Optional[str], Field(description="Optional rule description.")
    ] = None,
    rule_action: Annotated[
        Optional[str],
        Field(description="Action for the rule. Values: ALLOW, BLOCK, BYPASS, INSPECT")
    ] = None,
    enabled: Annotated[
        Optional[bool], Field(description="True to enable rule, False to disable.")
    ] = None,
    rank: Annotated[
        Optional[int], Field(description="Admin rank of the rule.")
    ] = None,
    order: Annotated[
        Optional[int], Field(description="Rule order, defaults to the bottom.")
    ] = None,
    src_ips: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Source IPs for the rule. Accepts IP addresses or CIDR. Accepts JSON string or list.")
    ] = None,
    dest_addresses: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Destination IPs for the rule. Accepts IP addresses, CIDR, or hostnames. Accepts JSON string or list.")
    ] = None,
    source_countries: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Source countries for the rule. Accepts JSON string or list.")
    ] = None,
    dest_countries: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Destination countries for the rule. Accepts JSON string or list.")
    ] = None,
    exclude_src_countries: Annotated[
        Optional[bool], Field(description="Exclude source countries from the rule.")
    ] = None,
    dest_ip_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(description="IP address categories for the rule. Accepts JSON string or list.")
    ] = None,
    device_trust_levels: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Device trust levels for the rule application. Values: ANY, UNKNOWN_DEVICETRUSTLEVEL, LOW_TRUST, MEDIUM_TRUST, HIGH_TRUST")
    ] = None,
    nw_applications: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Network service applications for the rule. Accepts JSON string or list.")
    ] = None,
    enable_full_logging: Annotated[
        Optional[bool], Field(description="If True, enables full logging.")
    ] = None,
    predefined: Annotated[
        Optional[bool], Field(description="Indicates that the rule is predefined by using a true value.")
    ] = None,
    default_rule: Annotated[
        Optional[bool], Field(description="Indicates whether the rule is the Default Cloud IPS Rule or not.")
    ] = None,
    app_services: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for application services for the rule.")
    ] = None,
    app_service_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for app service groups.")
    ] = None,
    departments: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for departments the rule applies to.")
    ] = None,
    dest_ip_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for destination IP groups.")
    ] = None,
    dest_ipv6_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for destination IPV6 groups.")
    ] = None,
    devices: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for devices managed by Zscaler Client Connector.")
    ] = None,
    device_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for device groups managed by Zscaler Client Connector.")
    ] = None,
    groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for groups the rule applies to.")
    ] = None,
    labels: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for labels the rule applies to.")
    ] = None,
    locations: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for locations the rule applies to.")
    ] = None,
    location_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for location groups.")
    ] = None,
    nw_application_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for network application groups.")
    ] = None,
    nw_services: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for network services the rule applies to.")
    ] = None,
    nw_service_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for network service groups.")
    ] = None,
    time_windows: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for time windows the rule applies to.")
    ] = None,
    users: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for users the rule applies to.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Updates an existing ZIA Cloud Firewall Rule.
    This is a write operation that requires the --enable-write-tools flag.

    Args:
        rule_id (int/str): The ID of the cloud firewall rule to update (required).
        [... additional parameters as documented in function signature ...]

    Returns:
        dict: The updated cloud firewall rule object.

    Example:
        Update a rule's action:
        >>> rule = zia_update_cloud_firewall_rule(
        ...     rule_id="12345",
        ...     rule_action="BLOCK",
        ...     enabled=False
        ... )
    """
    payload = _build_firewall_rule_payload(
        name=name,
        description=description,
        rule_action=rule_action,
        enabled=enabled,
        rank=rank,
        order=order,
        src_ips=src_ips,
        dest_addresses=dest_addresses,
        source_countries=source_countries,
        dest_countries=dest_countries,
        exclude_src_countries=exclude_src_countries,
        dest_ip_categories=dest_ip_categories,
        device_trust_levels=device_trust_levels,
        nw_applications=nw_applications,
        enable_full_logging=enable_full_logging,
        predefined=predefined,
        default_rule=default_rule,
        app_services=app_services,
        app_service_groups=app_service_groups,
        departments=departments,
        dest_ip_groups=dest_ip_groups,
        dest_ipv6_groups=dest_ipv6_groups,
        devices=devices,
        device_groups=device_groups,
        groups=groups,
        labels=labels,
        locations=locations,
        location_groups=location_groups,
        nw_application_groups=nw_application_groups,
        nw_services=nw_services,
        nw_service_groups=nw_service_groups,
        time_windows=time_windows,
        users=users,
    )

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    fw = client.zia.cloud_firewall_rules

    rule, _, err = fw.update_rule(rule_id, **payload)
    if err:
        raise Exception(f"Failed to update rule {rule_id}: {err}")
    return rule.as_dict()


def zia_delete_cloud_firewall_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the cloud firewall rule to delete.")
    ],
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}"
) -> str:
    """
    Deletes a ZIA Cloud Firewall Rule by ID.
    
    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.

    Args:
        rule_id (int/str): The ID of the cloud firewall rule to delete.
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "zia").

    Returns:
        str: Success message confirming deletion.

    Example:
        Delete a rule:
        >>> result = zia_delete_cloud_firewall_rule(rule_id="12345")
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zia_delete_cloud_firewall_rule",
        confirmed,
        {"rule_id": str(rule_id)}
    )
    if confirmation_check:
        return confirmation_check
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    fw = client.zia.cloud_firewall_rules

    _, _, err = fw.delete_rule(rule_id)
    if err:
        raise Exception(f"Failed to delete rule {rule_id}: {err}")
    return f"Cloud firewall rule {rule_id} deleted successfully."
