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


def _build_url_filtering_rule_payload(
    name: Optional[str] = None,
    description: Optional[str] = None,
    rule_action: Optional[str] = None,
    enabled: Optional[bool] = None,
    rank: Optional[int] = None,
    order: Optional[int] = None,
    protocols: Optional[Union[List[str], str]] = None,
    device_trust_levels: Optional[Union[List[str], str]] = None,
    url_categories: Optional[Union[List[str], str]] = None,
    url_categories2: Optional[Union[List[str], str]] = None,
    request_methods: Optional[Union[List[str], str]] = None,
    user_agent_types: Optional[Union[List[str], str]] = None,
    block_override: Optional[bool] = None,
    ciparule: Optional[bool] = None,
    end_user_notification_url: Optional[str] = None,
    enforce_time_validity: Optional[bool] = None,
    size_quota: Optional[str] = None,
    time_quota: Optional[str] = None,
    validity_start_time: Optional[str] = None,
    validity_end_time: Optional[str] = None,
    validity_time_zone_id: Optional[str] = None,
    departments: Optional[Union[List[int], str]] = None,
    devices: Optional[Union[List[int], str]] = None,
    device_groups: Optional[Union[List[int], str]] = None,
    groups: Optional[Union[List[int], str]] = None,
    labels: Optional[Union[List[int], str]] = None,
    locations: Optional[Union[List[int], str]] = None,
    location_groups: Optional[Union[List[int], str]] = None,
    time_windows: Optional[Union[List[int], str]] = None,
    users: Optional[Union[List[int], str]] = None,
    workload_groups: Optional[Union[List[int], str]] = None,
    override_users: Optional[Union[List[int], str]] = None,
    override_groups: Optional[Union[List[int], str]] = None,
) -> dict:
    """Build payload for URL filtering rule operations."""
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
        ("protocols", protocols),
        ("device_trust_levels", device_trust_levels),
        ("url_categories", url_categories),
        ("url_categories2", url_categories2),
        ("request_methods", request_methods),
        ("user_agent_types", user_agent_types),
        ("departments", departments),
        ("devices", devices),
        ("device_groups", device_groups),
        ("groups", groups),
        ("labels", labels),
        ("locations", locations),
        ("location_groups", location_groups),
        ("time_windows", time_windows),
        ("users", users),
        ("workload_groups", workload_groups),
        ("override_users", override_users),
        ("override_groups", override_groups),
    ]:
        if param_value is not None:
            payload[param_name] = _parse_list(param_value)

    # Boolean parameters
    if block_override is not None:
        payload["block_override"] = block_override
    if ciparule is not None:
        payload["ciparule"] = ciparule
    if enforce_time_validity is not None:
        payload["enforce_time_validity"] = enforce_time_validity

    # String parameters
    if end_user_notification_url is not None:
        payload["end_user_notification_url"] = end_user_notification_url
    if size_quota is not None:
        payload["size_quota"] = size_quota
    if time_quota is not None:
        payload["time_quota"] = time_quota
    if validity_start_time is not None:
        payload["validity_start_time"] = validity_start_time
    if validity_end_time is not None:
        payload["validity_end_time"] = validity_end_time
    if validity_time_zone_id is not None:
        payload["validity_time_zone_id"] = validity_time_zone_id

    return payload


# ============================================================================
# READ OPERATIONS (Read-Only)
# ============================================================================

def zia_list_url_filtering_rules(
    search: Annotated[
        Optional[str], Field(description="Optional search filter for listing rules by name.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[dict]:
    """
    Lists all ZIA URL Filtering Rules with optional search filtering.
    This is a read-only operation.

    URL Filtering Rules control access to websites based on their categories, protocols,
    request methods, user agents, and other attributes.

    Args:
        search (str, optional): Search string for filtering rules by name.
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "zia").

    Returns:
        list[dict]: List of URL filtering rule objects.

    Example:
        List all rules:
        >>> rules = zia_list_url_filtering_rules()

        Search for rules containing "block":
        >>> rules = zia_list_url_filtering_rules(search="block")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    url = client.zia.url_filtering

    query = {"search": search} if search else {}
    rules, _, err = url.list_rules(query_params=query)
    if err:
        raise Exception(f"Failed to list URL filtering rules: {err}")
    return [r.as_dict() for r in rules]


def zia_get_url_filtering_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the URL filtering rule to retrieve.")
    ],
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Gets a specific ZIA URL Filtering Rule by ID.
    This is a read-only operation.

    Args:
        rule_id (int/str): The ID of the URL filtering rule to retrieve.
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "zia").

    Returns:
        dict: The URL filtering rule object.

    Example:
        Get a specific rule:
        >>> rule = zia_get_url_filtering_rule(rule_id="12345")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    url = client.zia.url_filtering

    rule, _, err = url.get_rule(rule_id)
    if err:
        raise Exception(f"Failed to retrieve rule {rule_id}: {err}")
    return rule.as_dict()


# ============================================================================
# WRITE OPERATIONS (Require --enable-write-tools flag)
# ============================================================================

def zia_create_url_filtering_rule(
    name: Annotated[str, Field(description="Rule name (required).")],
    rule_action: Annotated[
        str,
        Field(description="Action taken when traffic matches rule criteria. Values: ANY, NONE, BLOCK, CAUTION, ALLOW, ICAP_RESPONSE")
    ],
    description: Annotated[
        Optional[str], Field(description="Optional rule description.")
    ] = None,
    enabled: Annotated[
        Optional[bool], Field(description="True to enable rule, False to disable.")
    ] = True,
    rank: Annotated[
        Optional[int], Field(description="The admin rank of the user who creates the rule.")
    ] = None,
    order: Annotated[
        Optional[int], Field(description="Order of execution of rule with respect to other URL Filtering rules.")
    ] = None,
    protocols: Annotated[
        Optional[Union[List[str], str]],
        Field(description="The protocol criteria for the rule. Accepts JSON string or list.")
    ] = None,
    device_trust_levels: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Device trust levels for which the rule must be applied. Values: ANY, UNKNOWN_DEVICETRUSTLEVEL, LOW_TRUST, MEDIUM_TRUST, HIGH_TRUST")
    ] = None,
    url_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(description="The names of URL categories that this rule applies to. Accepts JSON string or list.")
    ] = None,
    url_categories2: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Additional URL categories (connected with AND operator to url_categories). Accepts JSON string or list.")
    ] = None,
    request_methods: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Request methods that this rule will apply to. Values: CONNECT, DELETE, GET, HEAD, OPTIONS, OTHER, POST, PUT, TRACE")
    ] = None,
    user_agent_types: Annotated[
        Optional[Union[List[str], str]],
        Field(description="User Agent types on which this rule will be applied. Values: OPERA, FIREFOX, MSIE, MSEDGE, CHROME, SAFARI, OTHER, MSCHREDGE")
    ] = None,
    block_override: Annotated[
        Optional[bool], Field(description="When true, a BLOCK action triggered by the rule could be overridden.")
    ] = None,
    ciparule: Annotated[
        Optional[bool], Field(description="The CIPA compliance rule is enabled if this is set to True.")
    ] = None,
    end_user_notification_url: Annotated[
        Optional[str], Field(description="URL of end user notification page to be displayed when the rule is matched.")
    ] = None,
    enforce_time_validity: Annotated[
        Optional[bool], Field(description="Enforce a set validity time period for the URL Filtering rule.")
    ] = None,
    size_quota: Annotated[
        Optional[str], Field(description="Size quota in KB for applying the URL Filtering rule.")
    ] = None,
    time_quota: Annotated[
        Optional[str], Field(description="Time quota in minutes elapsed after the URL Filtering rule is applied.")
    ] = None,
    validity_start_time: Annotated[
        Optional[str], Field(description="Date and time the rule's effects will be valid from. Requires enforce_time_validity=True.")
    ] = None,
    validity_end_time: Annotated[
        Optional[str], Field(description="Date and time the rule's effects will end. Requires enforce_time_validity=True.")
    ] = None,
    validity_time_zone_id: Annotated[
        Optional[str], Field(description="Time zone ID for validity dates. Requires enforce_time_validity=True.")
    ] = None,
    departments: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the departments that this rule applies to.")
    ] = None,
    devices: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the devices that this rule applies to.")
    ] = None,
    device_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the device groups that this rule applies to.")
    ] = None,
    groups: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the groups that this rule applies to.")
    ] = None,
    labels: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the labels that this rule applies to.")
    ] = None,
    locations: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the locations that this rule applies to.")
    ] = None,
    location_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the location groups that this rule applies to.")
    ] = None,
    time_windows: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the time windows that this rule applies to.")
    ] = None,
    users: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the users that this rule applies to.")
    ] = None,
    workload_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the workload groups that this rule applies to.")
    ] = None,
    override_users: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs of users that this rule can be overridden for. Only applies if block_override=True, action=BLOCK.")
    ] = None,
    override_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs of groups that this rule can be overridden for. Only applies if block_override=True, action=BLOCK.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Creates a new ZIA URL Filtering Rule.
    This is a write operation that requires the --enable-write-tools flag.

    Args:
        name (str): Rule name (required).
        rule_action (str): Action taken when traffic matches rule criteria.
                          Values: ANY, NONE, BLOCK, CAUTION, ALLOW, ICAP_RESPONSE.
        [... additional parameters as documented in function signature ...]

    Returns:
        dict: The created URL filtering rule object.

    Example:
        Create a rule to block adult content:
        >>> rule = zia_create_url_filtering_rule(
        ...     name="Block Adult Content",
        ...     rule_action="BLOCK",
        ...     url_categories=["OTHER_ADULT_MATERIAL"],
        ...     protocols=["ANY_RULE"]
        ... )
    """
    payload = _build_url_filtering_rule_payload(
        name=name,
        description=description,
        rule_action=rule_action,
        enabled=enabled,
        rank=rank,
        order=order,
        protocols=protocols,
        device_trust_levels=device_trust_levels,
        url_categories=url_categories,
        url_categories2=url_categories2,
        request_methods=request_methods,
        user_agent_types=user_agent_types,
        block_override=block_override,
        ciparule=ciparule,
        end_user_notification_url=end_user_notification_url,
        enforce_time_validity=enforce_time_validity,
        size_quota=size_quota,
        time_quota=time_quota,
        validity_start_time=validity_start_time,
        validity_end_time=validity_end_time,
        validity_time_zone_id=validity_time_zone_id,
        departments=departments,
        devices=devices,
        device_groups=device_groups,
        groups=groups,
        labels=labels,
        locations=locations,
        location_groups=location_groups,
        time_windows=time_windows,
        users=users,
        workload_groups=workload_groups,
        override_users=override_users,
        override_groups=override_groups,
    )

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    url = client.zia.url_filtering

    rule, _, err = url.add_rule(**payload)
    if err:
        raise Exception(f"Failed to add URL filtering rule: {err}")
    return rule.as_dict()


def zia_update_url_filtering_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the URL filtering rule to update.")
    ],
    name: Annotated[
        Optional[str], Field(description="Rule name.")
    ] = None,
    description: Annotated[
        Optional[str], Field(description="Optional rule description.")
    ] = None,
    rule_action: Annotated[
        Optional[str],
        Field(description="Action taken when traffic matches rule criteria. Values: ANY, NONE, BLOCK, CAUTION, ALLOW, ICAP_RESPONSE")
    ] = None,
    enabled: Annotated[
        Optional[bool], Field(description="True to enable rule, False to disable.")
    ] = None,
    rank: Annotated[
        Optional[int], Field(description="The admin rank of the user who creates the rule.")
    ] = None,
    order: Annotated[
        Optional[int], Field(description="Order of execution of rule with respect to other URL Filtering rules.")
    ] = None,
    protocols: Annotated[
        Optional[Union[List[str], str]],
        Field(description="The protocol criteria for the rule. Accepts JSON string or list.")
    ] = None,
    device_trust_levels: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Device trust levels for which the rule must be applied. Values: ANY, UNKNOWN_DEVICETRUSTLEVEL, LOW_TRUST, MEDIUM_TRUST, HIGH_TRUST")
    ] = None,
    url_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(description="The names of URL categories that this rule applies to. Accepts JSON string or list.")
    ] = None,
    url_categories2: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Additional URL categories (connected with AND operator to url_categories). Accepts JSON string or list.")
    ] = None,
    request_methods: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Request methods that this rule will apply to. Values: CONNECT, DELETE, GET, HEAD, OPTIONS, OTHER, POST, PUT, TRACE")
    ] = None,
    user_agent_types: Annotated[
        Optional[Union[List[str], str]],
        Field(description="User Agent types on which this rule will be applied. Values: OPERA, FIREFOX, MSIE, MSEDGE, CHROME, SAFARI, OTHER, MSCHREDGE")
    ] = None,
    block_override: Annotated[
        Optional[bool], Field(description="When true, a BLOCK action triggered by the rule could be overridden.")
    ] = None,
    ciparule: Annotated[
        Optional[bool], Field(description="The CIPA compliance rule is enabled if this is set to True.")
    ] = None,
    end_user_notification_url: Annotated[
        Optional[str], Field(description="URL of end user notification page to be displayed when the rule is matched.")
    ] = None,
    enforce_time_validity: Annotated[
        Optional[bool], Field(description="Enforce a set validity time period for the URL Filtering rule.")
    ] = None,
    size_quota: Annotated[
        Optional[str], Field(description="Size quota in KB for applying the URL Filtering rule.")
    ] = None,
    time_quota: Annotated[
        Optional[str], Field(description="Time quota in minutes elapsed after the URL Filtering rule is applied.")
    ] = None,
    validity_start_time: Annotated[
        Optional[str], Field(description="Date and time the rule's effects will be valid from. Requires enforce_time_validity=True.")
    ] = None,
    validity_end_time: Annotated[
        Optional[str], Field(description="Date and time the rule's effects will end. Requires enforce_time_validity=True.")
    ] = None,
    validity_time_zone_id: Annotated[
        Optional[str], Field(description="Time zone ID for validity dates. Requires enforce_time_validity=True.")
    ] = None,
    departments: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the departments that this rule applies to.")
    ] = None,
    devices: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the devices that this rule applies to.")
    ] = None,
    device_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the device groups that this rule applies to.")
    ] = None,
    groups: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the groups that this rule applies to.")
    ] = None,
    labels: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the labels that this rule applies to.")
    ] = None,
    locations: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the locations that this rule applies to.")
    ] = None,
    location_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the location groups that this rule applies to.")
    ] = None,
    time_windows: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the time windows that this rule applies to.")
    ] = None,
    users: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the users that this rule applies to.")
    ] = None,
    workload_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs for the workload groups that this rule applies to.")
    ] = None,
    override_users: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs of users that this rule can be overridden for. Only applies if block_override=True, action=BLOCK.")
    ] = None,
    override_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="The IDs of groups that this rule can be overridden for. Only applies if block_override=True, action=BLOCK.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Updates an existing ZIA URL Filtering Rule.
    This is a write operation that requires the --enable-write-tools flag.

    Args:
        rule_id (int/str): The ID of the URL filtering rule to update (required).
        [... additional parameters as documented in function signature ...]

    Returns:
        dict: The updated URL filtering rule object.

    Example:
        Update a rule's action:
        >>> rule = zia_update_url_filtering_rule(
        ...     rule_id="12345",
        ...     rule_action="ALLOW",
        ...     enabled=True
        ... )
    """
    payload = _build_url_filtering_rule_payload(
        name=name,
        description=description,
        rule_action=rule_action,
        enabled=enabled,
        rank=rank,
        order=order,
        protocols=protocols,
        device_trust_levels=device_trust_levels,
        url_categories=url_categories,
        url_categories2=url_categories2,
        request_methods=request_methods,
        user_agent_types=user_agent_types,
        block_override=block_override,
        ciparule=ciparule,
        end_user_notification_url=end_user_notification_url,
        enforce_time_validity=enforce_time_validity,
        size_quota=size_quota,
        time_quota=time_quota,
        validity_start_time=validity_start_time,
        validity_end_time=validity_end_time,
        validity_time_zone_id=validity_time_zone_id,
        departments=departments,
        devices=devices,
        device_groups=device_groups,
        groups=groups,
        labels=labels,
        locations=locations,
        location_groups=location_groups,
        time_windows=time_windows,
        users=users,
        workload_groups=workload_groups,
        override_users=override_users,
        override_groups=override_groups,
    )

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    url = client.zia.url_filtering

    rule, _, err = url.update_rule(rule_id, **payload)
    if err:
        raise Exception(f"Failed to update rule {rule_id}: {err}")
    return rule.as_dict()


def zia_delete_url_filtering_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the URL filtering rule to delete.")
    ],
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}"
) -> str:
    """
    Deletes a ZIA URL Filtering Rule by ID.
    
    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.

    Args:
        rule_id (int/str): The ID of the URL filtering rule to delete.
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "zia").

    Returns:
        str: Success message confirming deletion.

    Example:
        Delete a rule:
        >>> result = zia_delete_url_filtering_rule(rule_id="12345")
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zia_delete_url_filtering_rule",
        confirmed,
        {"rule_id": str(rule_id)}
    )
    if confirmation_check:
        return confirmation_check
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    url = client.zia.url_filtering

    _, _, err = url.delete_rule(rule_id)
    if err:
        raise Exception(f"Failed to delete rule {rule_id}: {err}")
    return f"URL filtering rule {rule_id} deleted successfully."
