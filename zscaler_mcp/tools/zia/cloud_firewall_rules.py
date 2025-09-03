import json
from typing import Annotated, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zia_firewall_rule_manager(
    action: Annotated[
        Literal["list", "get", "add", "update", "delete"],
        Field(
            description="Cloud firewall rule operation: list, get, add, update, or delete."
        ),
    ] = "list",
    rule_id: Annotated[
        Optional[Union[int, str]],
        Field(description="Required for get, update, and delete operations."),
    ] = None,
    name: Annotated[
        Optional[str], Field(description="Rule name (required for add/update).")
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
    ] = True,
    search: Annotated[
        Optional[str], Field(description="Optional search filter for listing rules by name."),
    ] = None,
    # Core rule parameters
    rank: Annotated[
        Optional[int], Field(description="Admin rank of the rule.")
    ] = None,
    order: Annotated[
        Optional[int], Field(description="Rule order, defaults to the bottom.")
    ] = None,
    # IP and address parameters
    src_ips: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Source IPs for the rule. Accepts IP addresses or CIDR. Accepts JSON string or list.")
    ] = None,
    dest_addresses: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Destination IPs for the rule. Accepts IP addresses, CIDR, or hostnames. Accepts JSON string or list.")
    ] = None,
    # Country and category parameters
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
    # Device and application parameters
    device_trust_levels: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Device trust levels for the rule application. Values: ANY, UNKNOWN_DEVICETRUSTLEVEL, LOW_TRUST, MEDIUM_TRUST, HIGH_TRUST")
    ] = None,
    nw_applications: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Network service applications for the rule. Accepts JSON string or list.")
    ] = None,
    # Advanced parameters
    enable_full_logging: Annotated[
        Optional[bool], Field(description="If True, enables full logging.")
    ] = None,
    predefined: Annotated[
        Optional[bool], Field(description="Indicates that the rule is predefined by using a true value.")
    ] = None,
    default_rule: Annotated[
        Optional[bool], Field(description="Indicates whether the rule is the Default Cloud IPS Rule or not.")
    ] = None,
    # ID-based parameters (can be passed as JSON string or list)
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
) -> Union[dict, List[dict], str]:
    """
    Manages ZIA Cloud Firewall Rules for controlling network traffic based on IP addresses, countries, applications, and other criteria.

    Cloud Firewall Rules allow you to control network traffic based on source/destination IPs, countries,
    network applications, device trust levels, and other attributes. Rules can be configured to allow,
    block, bypass, or inspect matching traffic.

    Args:
        action (str): Operation to perform: list, get, add, update, or delete.
        rule_id (int/str, optional): Required for get, update, and delete operations.
        name (str, optional): Rule name (required for add/update).
        description (str, optional): Optional rule description.
        action (str, optional): Action for the rule. Values: ALLOW, BLOCK, BYPASS, INSPECT.
        enabled (bool, optional): True to enable rule, False to disable (default: True).
        search (str, optional): Search string for filtering rules by name.
        rank (int, optional): Admin rank of the rule.
        order (int, optional): Rule order, defaults to the bottom.
        src_ips (list/str, optional): Source IPs for the rule. Accepts IP addresses or CIDR.
        dest_addresses (list/str, optional): Destination IPs for the rule. Accepts IP addresses, CIDR, or hostnames.
        source_countries (list/str, optional): Source countries for the rule.
        dest_countries (list/str, optional): Destination countries for the rule.
        exclude_src_countries (bool, optional): Exclude source countries from the rule.
        dest_ip_categories (list/str, optional): IP address categories for the rule.
        device_trust_levels (list/str, optional): Device trust levels for rule application.
        nw_applications (list/str, optional): Network service applications for the rule.
        enable_full_logging (bool, optional): If True, enables full logging.
        predefined (bool, optional): Indicates that the rule is predefined.
        default_rule (bool, optional): Indicates whether the rule is the Default Cloud IPS Rule.
        app_services (list/str, optional): IDs for application services for the rule.
        app_service_groups (list/str, optional): IDs for app service groups.
        departments (list/str, optional): Department IDs the rule applies to.
        dest_ip_groups (list/str, optional): Destination IP group IDs.
        dest_ipv6_groups (list/str, optional): Destination IPV6 group IDs.
        devices (list/str, optional): Device IDs managed by Zscaler Client Connector.
        device_groups (list/str, optional): Device group IDs managed by Zscaler Client Connector.
        groups (list/str, optional): Group IDs the rule applies to.
        labels (list/str, optional): Label IDs the rule applies to.
        locations (list/str, optional): Location IDs the rule applies to.
        location_groups (list/str, optional): Location group IDs.
        nw_application_groups (list/str, optional): Network application group IDs.
        nw_services (list/str, optional): Network service IDs the rule applies to.
        nw_service_groups (list/str, optional): Network service group IDs.
        time_windows (list/str, optional): Time window IDs the rule applies to.
        users (list/str, optional): User IDs the rule applies to.

    Returns:
        dict | list[dict] | str: Rule object(s) or status message.

    Examples:
        List all cloud firewall rules:
        >>> rules = zia_firewall_rule_manager(action="list")

        Search for rules containing "block":
        >>> rules = zia_firewall_rule_manager(action="list", search="block")

        Get a specific rule:
        >>> rule = zia_firewall_rule_manager(action="get", rule_id="12345")

        Add a new rule to allow traffic to Google DNS:
        >>> rule = zia_firewall_rule_manager(
        ...     action="add",
        ...     name="Allow Google DNS",
        ...     action="ALLOW",
        ...     src_ips=["192.168.100.0/24", "192.168.200.1"],
        ...     dest_addresses=["8.8.8.8", "8.8.4.4"],
        ...     device_trust_levels=["UNKNOWN_DEVICETRUSTLEVEL", "LOW_TRUST", "MEDIUM_TRUST", "HIGH_TRUST"],
        ...     enable_full_logging=True
        ... )

        Add a rule to block malicious destinations:
        >>> rule = zia_firewall_rule_manager(
        ...     action="add",
        ...     name="Block Malicious IPs",
        ...     action="BLOCK",
        ...     dest_ip_categories=["BOTNET", "MALWARE_SITE", "PHISHING"],
        ...     dest_countries=["COUNTRY_RU", "COUNTRY_CN"],
        ...     device_trust_levels=["UNKNOWN_DEVICETRUSTLEVEL", "LOW_TRUST", "MEDIUM_TRUST", "HIGH_TRUST"]
        ... )

        Update an existing rule:
        >>> rule = zia_firewall_rule_manager(
        ...     action="update",
        ...     rule_id="12345",
        ...     name="Updated Rule Name",
        ...     action="BLOCK"
        ... )

        Delete a rule:
        >>> result = zia_firewall_rule_manager(action="delete", rule_id="12345")

    Note:
        - For list parameters, you can pass either a Python list or a JSON string.
        - The 'enabled' parameter is converted to 'state' (ENABLED/DISABLED) for the API.
        - IP addresses can be specified as individual IPs, CIDR notation, or hostnames.
        - Country codes should be in COUNTRY_XX format (e.g., COUNTRY_US, COUNTRY_CA).
        - Device trust levels determine which devices the rule applies to.
        - Network applications and services can be specified by name or ID.
    """
    # Helper function to parse list parameters
    def parse_list(val):
        if isinstance(val, str):
            try:
                return json.loads(val)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON string: {e}")
        return val

    # Build payload from parameters
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
            payload[param_name] = parse_list(param_value)

    # Boolean parameters
    if exclude_src_countries is not None:
        payload["exclude_src_countries"] = exclude_src_countries
    if enable_full_logging is not None:
        payload["enable_full_logging"] = enable_full_logging
    if predefined is not None:
        payload["predefined"] = predefined
    if default_rule is not None:
        payload["default_rule"] = default_rule

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    fw = client.zia.cloud_firewall_rules

    if action == "list":
        query = {"search": search} if search else {}
        rules, _, err = fw.list_rules(query_params=query)
        if err:
            raise Exception(f"Failed to list cloud firewall rules: {err}")
        return [r.as_dict() for r in rules]

    elif action == "get":
        if not rule_id:
            raise ValueError("rule_id is required for get.")
        rule, _, err = fw.get_rule(rule_id)
        if err:
            raise Exception(f"Failed to retrieve rule {rule_id}: {err}")
        return rule.as_dict()

    elif action == "add":
        if not name or not action:
            raise ValueError("name and action are required for add.")
        rule, _, err = fw.add_rule(**payload)
        if err:
            raise Exception(f"Failed to add cloud firewall rule: {err}")
        return rule.as_dict()

    elif action == "update":
        if not rule_id:
            raise ValueError("rule_id is required for update.")
        rule, _, err = fw.update_rule(rule_id, **payload)
        if err:
            raise Exception(f"Failed to update rule {rule_id}: {err}")
        return rule.as_dict()

    elif action == "delete":
        if not rule_id:
            raise ValueError("rule_id is required for delete.")
        _, _, err = fw.delete_rule(rule_id)
        if err:
            raise Exception(f"Failed to delete rule {rule_id}: {err}")
        return f"Cloud firewall rule {rule_id} deleted successfully."

    else:
        raise ValueError(f"Unsupported action: {action}")
