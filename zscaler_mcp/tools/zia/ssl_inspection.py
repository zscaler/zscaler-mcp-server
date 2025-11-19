import json
from typing import Annotated, Dict, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.utils.utils import parse_list

# ============================================================================
# Helper Functions
# ============================================================================


def _build_ssl_inspection_rule_payload(
    name: Optional[str] = None,
    action: Optional[Union[Dict, str]] = None,
    description: Optional[str] = None,
    enabled: Optional[bool] = None,
    rank: Optional[int] = None,
    order: Optional[int] = None,
    road_warrior_for_kerberos: Optional[bool] = None,
    predefined: Optional[bool] = None,
    default_rule: Optional[bool] = None,
    device_trust_levels: Optional[Union[List[str], str]] = None,
    user_agent_types: Optional[Union[List[str], str]] = None,
    platforms: Optional[Union[List[str], str]] = None,
    cloud_applications: Optional[Union[List[str], str]] = None,
    url_categories: Optional[Union[List[str], str]] = None,
    dest_ip_groups: Optional[Union[List[int], str]] = None,
    source_ip_groups: Optional[Union[List[int], str]] = None,
    devices: Optional[Union[List[int], str]] = None,
    device_groups: Optional[Union[List[int], str]] = None,
    groups: Optional[Union[List[int], str]] = None,
    users: Optional[Union[List[int], str]] = None,
    labels: Optional[Union[List[int], str]] = None,
    locations: Optional[Union[List[int], str]] = None,
    location_groups: Optional[Union[List[int], str]] = None,
    proxy_gateways: Optional[Union[List[int], str]] = None,
    time_windows: Optional[Union[List[int], str]] = None,
    workload_groups: Optional[Union[List[int], str]] = None,
    zpa_app_segments: Optional[Union[List[int], str]] = None,
) -> dict:
    """Build payload for SSL inspection rule operations."""
    payload = {}

    # Core parameters
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if enabled is not None:
        payload["enabled"] = enabled
    if rank is not None:
        payload["rank"] = rank
    if order is not None:
        payload["order"] = order

    # Action parameter - can be dict or JSON string
    if action is not None:
        if isinstance(action, str):
            try:
                action = json.loads(action)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON string for action: {exc}")
        if isinstance(action, dict):
            payload["action"] = action
        else:
            raise ValueError("Action must be a dictionary or JSON string")

    # List parameters that need parsing
    for param_name, param_value in [
        ("device_trust_levels", device_trust_levels),
        ("user_agent_types", user_agent_types),
        ("platforms", platforms),
        ("cloud_applications", cloud_applications),
        ("url_categories", url_categories),
        ("dest_ip_groups", dest_ip_groups),
        ("source_ip_groups", source_ip_groups),
        ("devices", devices),
        ("device_groups", device_groups),
        ("groups", groups),
        ("users", users),
        ("labels", labels),
        ("locations", locations),
        ("location_groups", location_groups),
        ("proxy_gateways", proxy_gateways),
        ("time_windows", time_windows),
        ("workload_groups", workload_groups),
        ("zpa_app_segments", zpa_app_segments),
    ]:
        if param_value is not None:
            payload[param_name] = parse_list(param_value)

    # Boolean parameters
    if road_warrior_for_kerberos is not None:
        payload["road_warrior_for_kerberos"] = road_warrior_for_kerberos
    if predefined is not None:
        payload["predefined"] = predefined
    if default_rule is not None:
        payload["default_rule"] = default_rule

    return payload


# ============================================================================
# READ OPERATIONS (Read-Only)
# ============================================================================


def zia_list_ssl_inspection_rules(
    search: Annotated[
        Optional[str], Field(description="Optional search filter for listing rules by name.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[dict]:
    """
    Lists all ZIA SSL Inspection Rules with optional search filtering.
    This is a read-only operation.

    SSL Inspection Rules control how Zscaler handles SSL/TLS encrypted traffic by determining
    which connections should be decrypted and inspected. These rules help balance security
    (by enabling inspection of encrypted traffic) with privacy and compliance requirements
    (by allowing certain traffic to bypass inspection).

    Rules are evaluated in order, and the first matching rule determines the action taken.
    Common actions include:
    - DO_NOT_INSPECT: Bypass SSL inspection for matching traffic
    - INSPECT: Decrypt and inspect SSL/TLS traffic
    - DO_NOT_DECRYPT: Do not decrypt but may apply other policies

    Args:
        search (str, optional): Search string for filtering rules by name.
            The search is case-insensitive and matches against rule names.
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "zia").

    Returns:
        list[dict]: List of SSL inspection rule objects, each containing:
            - id: Unique identifier for the rule
            - name: Rule name
            - description: Rule description
            - state: Rule state (ENABLED/DISABLED)
            - order: Rule order/priority
            - rank: Admin rank (1-7)
            - action: Action configuration (DO_NOT_INSPECT, INSPECT, etc.)
            - Matching criteria (cloud_applications, url_categories, groups, etc.)

    Example:
        List all SSL inspection rules:
        >>> rules = zia_list_ssl_inspection_rules()
        >>> print(f"Found {len(rules)} SSL inspection rules")

        Search for rules containing "banking":
        >>> rules = zia_list_ssl_inspection_rules(search="banking")
        >>> for rule in rules:
        ...     print(f"Rule: {rule['name']} (ID: {rule['id']})")

        List enabled rules and filter client-side:
        >>> all_rules = zia_list_ssl_inspection_rules()
        >>> enabled_rules = [r for r in all_rules if r.get('state') == 'ENABLED']
        >>> print(f"Found {len(enabled_rules)} enabled rules")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    ssl_inspection = client.zia.ssl_inspection_rules

    query = {"search": search} if search else {}
    rules, _, err = ssl_inspection.list_rules(query_params=query)
    if err:
        raise Exception(f"Failed to list SSL inspection rules: {err}")
    return [r.as_dict() for r in rules]


def zia_get_ssl_inspection_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the SSL inspection rule to retrieve.")
    ],
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Gets a specific ZIA SSL Inspection Rule by ID.
    This is a read-only operation.

    SSL Inspection Rules determine how Zscaler handles SSL/TLS encrypted traffic.
    Each rule can specify:
    - Action: Whether to inspect, bypass, or apply other policies
    - Matching criteria: Cloud applications, URL categories, user groups, locations, etc.
    - Conditions: Device trust levels, platforms, user agent types, etc.

    Args:
        rule_id (int/str): The ID of the SSL inspection rule to retrieve.
            This is the unique identifier assigned when the rule was created.
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "zia").

    Returns:
        dict: The SSL inspection rule object containing:
            - id: Unique identifier for the rule
            - name: Rule name (max 31 characters)
            - description: Additional information about the rule
            - state: Rule state (ENABLED or DISABLED)
            - order: Rule order/priority in the evaluation sequence
            - rank: Admin rank (1-7, where 7 is the highest)
            - action: Action configuration object with type and sub-actions
            - predefined: Whether the rule is predefined by Zscaler
            - default_rule: Whether this is the default SSL inspection rule
            - Matching criteria:
                - cloud_applications: List of cloud application names
                - url_categories: List of URL category names
                - groups: List of user group IDs
                - users: List of user IDs
                - locations: List of location IDs
                - location_groups: List of location group IDs
                - devices: List of device IDs
                - device_groups: List of device group IDs
                - labels: List of label IDs
                - dest_ip_groups: List of destination IP group IDs
                - source_ip_groups: List of source IP group IDs
                - time_windows: List of time window IDs
                - device_trust_levels: List of device trust levels
                - platforms: List of platform types
                - user_agent_types: List of user agent types
                - proxy_gateways: List of proxy gateway IDs
                - workload_groups: List of workload group IDs
                - zpa_app_segments: List of ZPA application segment IDs
            - road_warrior_for_kerberos: Whether rule applies to remote users with PAC/Kerberos

    Raises:
        Exception: If the rule is not found or if there's an error retrieving it.

    Example:
        Get a specific rule by ID:
        >>> rule = zia_get_ssl_inspection_rule(rule_id="12345")
        >>> print(f"Rule: {rule['name']}")
        >>> print(f"State: {rule['state']}")
        >>> print(f"Action: {rule.get('action', {}).get('type', 'N/A')}")

        Get rule details and check matching criteria:
        >>> rule = zia_get_ssl_inspection_rule(rule_id="67890")
        >>> if rule.get('cloud_applications'):
        ...     print(f"Applies to: {', '.join(rule['cloud_applications'])}")
        >>> if rule.get('url_categories'):
        ...     print(f"URL Categories: {', '.join(rule['url_categories'])}")

        Verify rule configuration:
        >>> rule = zia_get_ssl_inspection_rule(rule_id="11111")
        >>> print(f"Order: {rule.get('order')}")
        >>> print(f"Rank: {rule.get('rank')}")
        >>> print(f"Predefined: {rule.get('predefined', False)}")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    ssl_inspection = client.zia.ssl_inspection_rules

    rule, _, err = ssl_inspection.get_rule(rule_id)
    if err:
        raise Exception(f"Failed to retrieve SSL inspection rule {rule_id}: {err}")
    return rule.as_dict()


# ============================================================================
# WRITE OPERATIONS (Require --enable-write-tools flag)
# ============================================================================

def zia_create_ssl_inspection_rule(
    name: Annotated[str, Field(description="Rule name (required, max 31 characters).")],
    action: Annotated[
        Union[Dict, str],
        Field(
            description=(
                "Action configuration for the rule (required). Can be a dictionary or JSON string. "
                "Action types: DO_NOT_INSPECT, INSPECT, DO_NOT_DECRYPT. "
                "Example: {\"type\": \"DO_NOT_DECRYPT\", \"do_not_decrypt_sub_actions\": {...}}"
            )
        ),
    ],
    description: Annotated[
        Optional[str], Field(description="Optional rule description.")
    ] = None,
    enabled: Annotated[
        Optional[bool], Field(description="True to enable rule, False to disable (default: True).")
    ] = True,
    rank: Annotated[
        Optional[int], Field(description="Admin rank of the rule (1-7, where 7 is the highest).")
    ] = None,
    order: Annotated[
        Optional[int], Field(description="Rule order/priority, defaults to the bottom of the list.")
    ] = None,
    road_warrior_for_kerberos: Annotated[
        Optional[bool],
        Field(description="If True, the rule is applied to remote users that use PAC with Kerberos authentication.")
    ] = None,
    predefined: Annotated[
        Optional[bool], Field(description="Indicates that the rule is predefined by using a true value.")
    ] = None,
    default_rule: Annotated[
        Optional[bool], Field(description="Indicates whether the rule is the Default Cloud SSL Inspection Rule or not.")
    ] = None,
    device_trust_levels: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Device trust levels for which the rule must be applied. "
                "Values: ANY, UNKNOWN_DEVICETRUSTLEVEL, LOW_TRUST, MEDIUM_TRUST, HIGH_TRUST. "
                "Accepts JSON string or list."
            )
        )
    ] = None,
    user_agent_types: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "User Agent types on which this rule will be applied. "
                "Values: OPERA, FIREFOX, MSIE, MSEDGE, CHROME, SAFARI, OTHER, MSCHREDGE. "
                "Accepts JSON string or list."
            )
        )
    ] = None,
    platforms: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Platform types for which the rule must be applied. "
                "Values: SCAN_IOS, SCAN_ANDROID, SCAN_MACOS, SCAN_WINDOWS, NO_CLIENT_CONNECTOR, SCAN_LINUX. "
                "Accepts JSON string or list."
            )
        )
    ] = None,
    cloud_applications: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Cloud applications for which the SSL inspection rule is applied. "
                "Accepts cloud application names (e.g., 'CHATGPT_AI', 'ANDI'). "
                "Accepts JSON string or list."
            )
        )
    ] = None,
    url_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "URL categories for which the rule must be applied. "
                "Accepts URL category names. Accepts JSON string or list."
            )
        )
    ] = None,
    dest_ip_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for destination IP groups. Accepts JSON string or list.")
    ] = None,
    source_ip_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for source IP groups. Accepts JSON string or list.")
    ] = None,
    devices: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for devices managed by Zscaler Client Connector. Accepts JSON string or list.")
    ] = None,
    device_groups: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for device groups managed by Zscaler Client Connector. Accepts JSON string or list.")
    ] = None,
    groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for user groups the rule applies to. Accepts JSON string or list.")
    ] = None,
    users: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for users the rule applies to. Accepts JSON string or list.")
    ] = None,
    labels: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for labels the rule applies to. Accepts JSON string or list.")
    ] = None,
    locations: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for locations the rule applies to. Accepts JSON string or list.")
    ] = None,
    location_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for location groups. Accepts JSON string or list.")
    ] = None,
    proxy_gateways: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for proxy chaining gateways for which this rule is applicable. Accepts JSON string or list.")
    ] = None,
    time_windows: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for time windows the rule applies to. Accepts JSON string or list.")
    ] = None,
    workload_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for workload groups for which this rule is applicable. Accepts JSON string or list.")
    ] = None,
    zpa_app_segments: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for Source IP Anchoring-enabled ZPA Application Segments. Accepts JSON string or list.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Creates a new ZIA SSL Inspection Rule.
    This is a write operation that requires the --enable-write-tools flag.

    SSL Inspection Rules determine how Zscaler handles SSL/TLS encrypted traffic by specifying
    which connections should be decrypted and inspected. These rules are critical for balancing
    security (enabling inspection of encrypted traffic) with privacy and compliance requirements
    (allowing certain traffic to bypass inspection).

    Rules are evaluated in order, and the first matching rule determines the action taken.
    The action parameter defines what happens when traffic matches the rule criteria.

    IMPORTANT PAYLOAD FORMAT:
    - All list parameters (groups, users, labels, etc.) MUST be Python lists of integers: [12345, 67890]
    - String list parameters (cloud_applications, url_categories, platforms, etc.) MUST be Python lists of strings: ["APP1", "APP2"]
    - The 'action' parameter MUST be a Python dictionary with the exact structure shown in examples
    - Do NOT send list parameters as JSON strings - use actual Python lists
    - The 'enabled' parameter accepts boolean (True/False) which is automatically converted to state

    Args:
        name (str): Rule name (required, max 31 characters).
        action (dict/str): Action configuration (required). Can be a dictionary or JSON string.
            Common action types:
            - DO_NOT_INSPECT: Bypass SSL inspection for matching traffic
            - INSPECT: Decrypt and inspect SSL/TLS traffic
            - DO_NOT_DECRYPT: Do not decrypt but may apply other policies
            
            Action structure example:
            {
                "type": "DO_NOT_DECRYPT",
                "do_not_decrypt_sub_actions": {
                    "bypass_other_policies": True,
                    "block_ssl_traffic_with_no_sni_enabled": True,
                    "min_tls_version": "SERVER_TLS_1_0"
                }
            }
        description (str, optional): Optional rule description.
        enabled (bool, optional): True to enable rule, False to disable (default: True).
        rank (int, optional): Admin rank of the rule (1-7, where 7 is the highest).
        order (int, optional): Rule order/priority, defaults to the bottom of the list.
        road_warrior_for_kerberos (bool, optional): If True, applies to remote users using PAC with Kerberos.
        predefined (bool, optional): Indicates that the rule is predefined.
        default_rule (bool, optional): Indicates whether this is the Default Cloud SSL Inspection Rule.
        device_trust_levels (list/str, optional): Device trust levels. Values: ANY, UNKNOWN_DEVICETRUSTLEVEL,
            LOW_TRUST, MEDIUM_TRUST, HIGH_TRUST.
        user_agent_types (list/str, optional): User Agent types. Values: OPERA, FIREFOX, MSIE, MSEDGE,
            CHROME, SAFARI, OTHER, MSCHREDGE.
        platforms (list/str, optional): Platform types. Values: SCAN_IOS, SCAN_ANDROID, SCAN_MACOS,
            SCAN_WINDOWS, NO_CLIENT_CONNECTOR, SCAN_LINUX.
        cloud_applications (list/str, optional): Cloud application names (e.g., 'CHATGPT_AI', 'ANDI').
        url_categories (list/str, optional): URL category names.
        dest_ip_groups (list/int/str, optional): IDs for destination IP groups.
        source_ip_groups (list/int/str, optional): IDs for source IP groups.
        devices (list/int/str, optional): IDs for devices managed by Zscaler Client Connector.
        device_groups (list/int/str, optional): IDs for device groups.
        groups (list/int/str, optional): IDs for user groups.
        users (list/int/str, optional): IDs for users.
        labels (list/int/str, optional): IDs for labels.
        locations (list/int/str, optional): IDs for locations.
        location_groups (list/int/str, optional): IDs for location groups.
        proxy_gateways (list/int/str, optional): IDs for proxy chaining gateways.
        time_windows (list/int/str, optional): IDs for time windows.
        workload_groups (list/int/str, optional): IDs for workload groups.
        zpa_app_segments (list/int/str, optional): IDs for ZPA Application Segments.
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "zia").

    Returns:
        dict: The created SSL inspection rule object with all its properties.

    Raises:
        ValueError: If action is not a valid dictionary or JSON string.
        Exception: If the rule creation fails.

    Example:
        CORRECT FORMAT - Create a complete rule (this is the exact format to use):
        >>> rule = zia_create_ssl_inspection_rule(
        ...     name="SSL Bypass Rule",
        ...     action={
        ...         "type": "DO_NOT_DECRYPT",
        ...         "do_not_decrypt_sub_actions": {
        ...             "bypass_other_policies": True,
        ...             "block_ssl_traffic_with_no_sni_enabled": True,
        ...             "min_tls_version": "SERVER_TLS_1_0"
        ...         }
        ...     },
        ...     description="Bypass SSL inspection for specific apps",
        ...     enabled=True,
        ...     order=1,
        ...     rank=7,
        ...     road_warrior_for_kerberos=True,
        ...     cloud_applications=["CHATGPT_AI", "ANDI"],
        ...     url_categories=["OTHER_ADULT_MATERIAL"],
        ...     platforms=["SCAN_IOS", "SCAN_ANDROID", "SCAN_MACOS", "SCAN_WINDOWS", "NO_CLIENT_CONNECTOR", "SCAN_LINUX"],
        ...     labels=[2930713],
        ...     groups=[62718414],
        ...     departments=[68759308]
        ... )

        Create a simple DO_NOT_INSPECT rule:
        >>> rule = zia_create_ssl_inspection_rule(
        ...     name="Bypass Banking Apps",
        ...     action={"type": "DO_NOT_INSPECT"},
        ...     description="Bypass SSL inspection for banking applications",
        ...     cloud_applications=["BANKING", "FINANCIAL_SERVICES"],
        ...     enabled=True,
        ...     rank=7
        ... )

        Create with device and platform criteria (IMPORTANT: use Python lists, not JSON strings):
        >>> rule = zia_create_ssl_inspection_rule(
        ...     name="High Trust Devices",
        ...     action={"type": "INSPECT"},
        ...     platforms=["SCAN_WINDOWS", "SCAN_MACOS"],
        ...     device_trust_levels=["HIGH_TRUST", "MEDIUM_TRUST"],
        ...     groups=[12345, 67890],
        ...     users=[98765, 54321],
        ...     enabled=True
        ... )

        Create with user and location scoping:
        >>> rule = zia_create_ssl_inspection_rule(
        ...     name="Corporate Users Only",
        ...     action={"type": "INSPECT"},
        ...     groups=[95016183],
        ...     users=[95016194],
        ...     locations=[12345, 67890],
        ...     location_groups=[5001],
        ...     enabled=True,
        ...     rank=7,
        ...     road_warrior_for_kerberos=True
        ... )
    """
    payload = _build_ssl_inspection_rule_payload(
        name=name,
        action=action,
        description=description,
        enabled=enabled,
        rank=rank,
        order=order,
        road_warrior_for_kerberos=road_warrior_for_kerberos,
        predefined=predefined,
        default_rule=default_rule,
        device_trust_levels=device_trust_levels,
        user_agent_types=user_agent_types,
        platforms=platforms,
        cloud_applications=cloud_applications,
        url_categories=url_categories,
        dest_ip_groups=dest_ip_groups,
        source_ip_groups=source_ip_groups,
        devices=devices,
        device_groups=device_groups,
        groups=groups,
        users=users,
        labels=labels,
        locations=locations,
        location_groups=location_groups,
        proxy_gateways=proxy_gateways,
        time_windows=time_windows,
        workload_groups=workload_groups,
        zpa_app_segments=zpa_app_segments,
    )

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    ssl_inspection = client.zia.ssl_inspection_rules

    rule, _, err = ssl_inspection.add_rule(**payload)
    if err:
        raise Exception(f"Failed to add SSL inspection rule: {err}")
    return rule.as_dict()


def zia_update_ssl_inspection_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the SSL inspection rule to update (required).")
    ],
    name: Annotated[
        Optional[str], Field(description="Rule name (max 31 characters).")
    ] = None,
    action: Annotated[
        Optional[Union[Dict, str]],
        Field(
            description=(
                "Action configuration for the rule. Can be a dictionary or JSON string. "
                "Action types: DO_NOT_INSPECT, INSPECT, DO_NOT_DECRYPT. "
                "Example: {\"type\": \"DO_NOT_DECRYPT\", \"do_not_decrypt_sub_actions\": {...}}"
            )
        ),
    ] = None,
    description: Annotated[
        Optional[str], Field(description="Optional rule description.")
    ] = None,
    enabled: Annotated[
        Optional[bool], Field(description="True to enable rule, False to disable.")
    ] = None,
    rank: Annotated[
        Optional[int], Field(description="Admin rank of the rule (1-7, where 7 is the highest).")
    ] = None,
    order: Annotated[
        Optional[int], Field(description="Rule order/priority.")
    ] = None,
    road_warrior_for_kerberos: Annotated[
        Optional[bool],
        Field(description="If True, the rule is applied to remote users that use PAC with Kerberos authentication.")
    ] = None,
    predefined: Annotated[
        Optional[bool], Field(description="Indicates that the rule is predefined by using a true value.")
    ] = None,
    default_rule: Annotated[
        Optional[bool], Field(description="Indicates whether the rule is the Default Cloud SSL Inspection Rule or not.")
    ] = None,
    device_trust_levels: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Device trust levels for which the rule must be applied. "
                "Values: ANY, UNKNOWN_DEVICETRUSTLEVEL, LOW_TRUST, MEDIUM_TRUST, HIGH_TRUST. "
                "Accepts JSON string or list."
            )
        )
    ] = None,
    user_agent_types: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "User Agent types on which this rule will be applied. "
                "Values: OPERA, FIREFOX, MSIE, MSEDGE, CHROME, SAFARI, OTHER, MSCHREDGE. "
                "Accepts JSON string or list."
            )
        )
    ] = None,
    platforms: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Platform types for which the rule must be applied. "
                "Values: SCAN_IOS, SCAN_ANDROID, SCAN_MACOS, SCAN_WINDOWS, NO_CLIENT_CONNECTOR, SCAN_LINUX. "
                "Accepts JSON string or list."
            )
        )
    ] = None,
    cloud_applications: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Cloud applications for which the SSL inspection rule is applied. "
                "Accepts cloud application names (e.g., 'CHATGPT_AI', 'ANDI'). "
                "Accepts JSON string or list."
            )
        )
    ] = None,
    url_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "URL categories for which the rule must be applied. "
                "Accepts URL category names. Accepts JSON string or list."
            )
        )
    ] = None,
    dest_ip_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for destination IP groups. Accepts JSON string or list.")
    ] = None,
    source_ip_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for source IP groups. Accepts JSON string or list.")
    ] = None,
    devices: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for devices managed by Zscaler Client Connector. Accepts JSON string or list.")
    ] = None,
    device_groups: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for device groups managed by Zscaler Client Connector. Accepts JSON string or list.")
    ] = None,
    groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for user groups the rule applies to. Accepts JSON string or list.")
    ] = None,
    users: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for users the rule applies to. Accepts JSON string or list.")
    ] = None,
    labels: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for labels the rule applies to. Accepts JSON string or list.")
    ] = None,
    locations: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for locations the rule applies to. Accepts JSON string or list.")
    ] = None,
    location_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for location groups. Accepts JSON string or list.")
    ] = None,
    proxy_gateways: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for proxy chaining gateways for which this rule is applicable. Accepts JSON string or list.")
    ] = None,
    time_windows: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for time windows the rule applies to. Accepts JSON string or list.")
    ] = None,
    workload_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for workload groups for which this rule is applicable. Accepts JSON string or list.")
    ] = None,
    zpa_app_segments: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for Source IP Anchoring-enabled ZPA Application Segments. Accepts JSON string or list.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Updates an existing ZIA SSL Inspection Rule.
    This is a write operation that requires the --enable-write-tools flag.

    SSL Inspection Rules determine how Zscaler handles SSL/TLS encrypted traffic by specifying
    which connections should be decrypted and inspected. This function allows you to modify
    an existing rule's configuration, including its action, matching criteria, and other settings.

    Only the parameters you provide will be updated; omitted parameters will remain unchanged.

    IMPORTANT PAYLOAD FORMAT:
    - All list parameters (groups, users, labels, etc.) MUST be Python lists of integers: [12345, 67890]
    - String list parameters (cloud_applications, url_categories, platforms, etc.) MUST be Python lists of strings: ["APP1", "APP2"]
    - The 'action' parameter MUST be a Python dictionary with the exact structure shown in examples
    - Do NOT send list parameters as JSON strings - use actual Python lists
    - The 'enabled' parameter accepts boolean (True/False) which is automatically converted to state

    Args:
        rule_id (int/str): The ID of the SSL inspection rule to update (required).
        name (str, optional): Rule name (max 31 characters).
        action (dict/str, optional): Action configuration. Can be a dictionary or JSON string.
            Common action types:
            - DO_NOT_INSPECT: Bypass SSL inspection for matching traffic
            - INSPECT: Decrypt and inspect SSL/TLS traffic
            - DO_NOT_DECRYPT: Do not decrypt but may apply other policies
            
            Action structure example:
            {
                "type": "DO_NOT_DECRYPT",
                "do_not_decrypt_sub_actions": {
                    "bypass_other_policies": True,
                    "block_ssl_traffic_with_no_sni_enabled": True,
                    "min_tls_version": "SERVER_TLS_1_2"
                }
            }
        description (str, optional): Optional rule description.
        enabled (bool, optional): True to enable rule, False to disable.
        rank (int, optional): Admin rank of the rule (1-7, where 7 is the highest).
        order (int, optional): Rule order/priority in the evaluation sequence.
        road_warrior_for_kerberos (bool, optional): If True, applies to remote users using PAC with Kerberos.
        predefined (bool, optional): Indicates that the rule is predefined.
        default_rule (bool, optional): Indicates whether this is the Default Cloud SSL Inspection Rule.
        device_trust_levels (list/str, optional): Device trust levels. Values: ANY, UNKNOWN_DEVICETRUSTLEVEL,
            LOW_TRUST, MEDIUM_TRUST, HIGH_TRUST.
        user_agent_types (list/str, optional): User Agent types. Values: OPERA, FIREFOX, MSIE, MSEDGE,
            CHROME, SAFARI, OTHER, MSCHREDGE.
        platforms (list/str, optional): Platform types. Values: SCAN_IOS, SCAN_ANDROID, SCAN_MACOS,
            SCAN_WINDOWS, NO_CLIENT_CONNECTOR, SCAN_LINUX.
        cloud_applications (list/str, optional): Cloud application names (e.g., 'CHATGPT_AI', 'ANDI').
        url_categories (list/str, optional): URL category names.
        dest_ip_groups (list/int/str, optional): IDs for destination IP groups.
        source_ip_groups (list/int/str, optional): IDs for source IP groups.
        devices (list/int/str, optional): IDs for devices managed by Zscaler Client Connector.
        device_groups (list/int/str, optional): IDs for device groups.
        groups (list/int/str, optional): IDs for user groups.
        users (list/int/str, optional): IDs for users.
        labels (list/int/str, optional): IDs for labels.
        locations (list/int/str, optional): IDs for locations.
        location_groups (list/int/str, optional): IDs for location groups.
        proxy_gateways (list/int/str, optional): IDs for proxy chaining gateways.
        time_windows (list/int/str, optional): IDs for time windows.
        workload_groups (list/int/str, optional): IDs for workload groups.
        zpa_app_segments (list/int/str, optional): IDs for ZPA Application Segments.
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "zia").

    Returns:
        dict: The updated SSL inspection rule object with all its properties.

    Raises:
        ValueError: If action is not a valid dictionary or JSON string.
        Exception: If the rule update fails.

    Example:
        CORRECT FORMAT - Update rule with all parameters (this is the exact format to use):
        >>> rule = zia_update_ssl_inspection_rule(
        ...     rule_id="1526911",
        ...     name="Updated SSL Rule",
        ...     description="Updated rule description",
        ...     enabled=True,
        ...     order=1,
        ...     rank=7,
        ...     road_warrior_for_kerberos=True,
        ...     cloud_applications=["CHATGPT_AI", "ANDI"],
        ...     url_categories=["OTHER_ADULT_MATERIAL"],
        ...     platforms=["SCAN_IOS", "SCAN_ANDROID", "SCAN_MACOS", "SCAN_WINDOWS", "NO_CLIENT_CONNECTOR", "SCAN_LINUX"],
        ...     labels=[2930713],
        ...     groups=[62718414],
        ...     departments=[68759308],
        ...     action={
        ...         "type": "DO_NOT_DECRYPT",
        ...         "do_not_decrypt_sub_actions": {
        ...             "bypass_other_policies": True,
        ...             "block_ssl_traffic_with_no_sni_enabled": True,
        ...             "min_tls_version": "SERVER_TLS_1_0"
        ...         }
        ...     }
        ... )

        Update only specific fields (minimal update):
        >>> rule = zia_update_ssl_inspection_rule(
        ...     rule_id="12345",
        ...     enabled=False,
        ...     description="Temporarily disabled"
        ... )

        Update action to DO_NOT_INSPECT:
        >>> rule = zia_update_ssl_inspection_rule(
        ...     rule_id="67890",
        ...     action={"type": "DO_NOT_INSPECT"}
        ... )

        Update matching criteria with lists (IMPORTANT: use Python lists, not JSON strings):
        >>> rule = zia_update_ssl_inspection_rule(
        ...     rule_id="22222",
        ...     cloud_applications=["CHATGPT_AI", "GITHUB_COPILOT", "CLAUDE_AI"],
        ...     groups=[12345, 67890, 11111],
        ...     users=[98765, 54321]
        ... )

        Update priority and scope:
        >>> rule = zia_update_ssl_inspection_rule(
        ...     rule_id="33333",
        ...     order=1,
        ...     rank=7,
        ...     locations=[10001, 10002],
        ...     location_groups=[5001]
        ... )

        Update device and platform criteria:
        >>> rule = zia_update_ssl_inspection_rule(
        ...     rule_id="44444",
        ...     platforms=["SCAN_WINDOWS", "SCAN_MACOS"],
        ...     device_trust_levels=["HIGH_TRUST", "MEDIUM_TRUST"],
        ...     user_agent_types=["CHROME", "FIREFOX", "SAFARI"]
        ... )
    """
    payload = _build_ssl_inspection_rule_payload(
        name=name,
        action=action,
        description=description,
        enabled=enabled,
        rank=rank,
        order=order,
        road_warrior_for_kerberos=road_warrior_for_kerberos,
        predefined=predefined,
        default_rule=default_rule,
        device_trust_levels=device_trust_levels,
        user_agent_types=user_agent_types,
        platforms=platforms,
        cloud_applications=cloud_applications,
        url_categories=url_categories,
        dest_ip_groups=dest_ip_groups,
        source_ip_groups=source_ip_groups,
        devices=devices,
        device_groups=device_groups,
        groups=groups,
        users=users,
        labels=labels,
        locations=locations,
        location_groups=location_groups,
        proxy_gateways=proxy_gateways,
        time_windows=time_windows,
        workload_groups=workload_groups,
        zpa_app_segments=zpa_app_segments,
    )

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    ssl_inspection = client.zia.ssl_inspection_rules

    rule, _, err = ssl_inspection.update_rule(rule_id, **payload)
    if err:
        raise Exception(f"Failed to update SSL inspection rule {rule_id}: {err}")
    return rule.as_dict()


def zia_delete_ssl_inspection_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the SSL inspection rule to delete.")
    ],
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}"
) -> str:
    """
    Deletes a ZIA SSL Inspection Rule by ID.
    This is a write operation that requires the --enable-write-tools flag.
    
    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone. Once deleted, the SSL inspection rule and all its
    configuration will be permanently removed from your Zscaler organization.

    SSL Inspection Rules determine how Zscaler handles SSL/TLS encrypted traffic by specifying
    which connections should be decrypted and inspected. Deleting a rule may impact your
    organization's security posture and traffic handling, so ensure you understand the
    implications before proceeding.

    Args:
        rule_id (int/str): The unique identifier for the SSL inspection rule to delete.
            This is the ID assigned when the rule was created. You can find rule IDs
            by listing all rules using zia_list_ssl_inspection_rules().
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "zia").

    Returns:
        str: Success message confirming the deletion of the rule.

    Raises:
        Exception: If the rule deletion fails (e.g., rule not found, insufficient permissions,
            or rule is protected/predefined and cannot be deleted).

    Example:
        Delete a specific SSL inspection rule:
        >>> result = zia_delete_ssl_inspection_rule(rule_id="12345")
        >>> print(result)
        "SSL inspection rule 12345 deleted successfully."

        Delete a rule after verifying it exists:
        >>> # First, verify the rule exists
        >>> rule = zia_get_ssl_inspection_rule(rule_id="67890")
        >>> print(f"About to delete: {rule['name']}")
        >>> # Then delete it
        >>> result = zia_delete_ssl_inspection_rule(rule_id="67890")
        >>> print(result)

        Delete multiple rules (requires calling this function multiple times):
        >>> rule_ids = ["11111", "22222", "33333"]
        >>> for rule_id in rule_ids:
        ...     result = zia_delete_ssl_inspection_rule(rule_id=rule_id)
        ...     print(result)
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zia_delete_ssl_inspection_rule",
        confirmed,
        {"rule_id": str(rule_id)}
    )
    if confirmation_check:
        return confirmation_check
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    ssl_inspection = client.zia.ssl_inspection_rules

    _, _, err = ssl_inspection.delete_rule(rule_id)
    if err:
        raise Exception(f"Failed to delete SSL inspection rule {rule_id}: {err}")
    return f"SSL inspection rule {rule_id} deleted successfully."
