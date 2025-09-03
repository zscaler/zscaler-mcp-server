import json
from typing import Annotated, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zia_url_filtering_rule_manager(
    action: Annotated[
        Literal["list", "get", "add", "update", "delete"],
        Field(
            description="URL filtering rule operation: list, get, add, update, or delete."
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
        Field(description="Action taken when traffic matches rule criteria. Accepted values: ANY, NONE, BLOCK, CAUTION, ALLOW, ICAP_RESPONSE")
    ] = None,
    enabled: Annotated[
        Optional[bool], Field(description="True to enable rule, False to disable.")
    ] = True,
    search: Annotated[
        Optional[str], Field(description="Optional search filter for listing rules by name."),
    ] = None,
    # Core rule parameters
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
    # Advanced parameters
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
    # ID-based parameters (can be passed as JSON string or list)
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
) -> Union[dict, List[dict], str]:
    """
    Manages ZIA URL Filtering Rules for controlling web traffic based on URL categories, protocols, and other criteria.

    URL Filtering Rules allow you to control access to websites based on their categories, protocols,
    request methods, user agents, and other attributes. Rules can be configured to allow, block,
    or apply caution actions to matching traffic.

    Args:
        action (str): Operation to perform: list, get, add, update, or delete.
        rule_id (int/str, optional): Required for get, update, and delete operations.
        name (str, optional): Rule name (required for add/update).
        description (str, optional): Optional rule description.
        action (str, optional): Action taken when traffic matches rule criteria.
                               Values: ANY, NONE, BLOCK, CAUTION, ALLOW, ICAP_RESPONSE.
        enabled (bool, optional): True to enable rule, False to disable (default: True).
        search (str, optional): Search string for filtering rules by name.
        rank (int, optional): The admin rank of the user who creates the rule.
        order (int, optional): Order of execution relative to other rules.
        protocols (list/str, optional): Protocol criteria for the rule.
        device_trust_levels (list/str, optional): Device trust levels for rule application.
        url_categories (list/str, optional): URL categories that the rule applies to.
        url_categories2 (list/str, optional): Additional URL categories (AND operator with url_categories).
        request_methods (list/str, optional): HTTP request methods the rule applies to.
        user_agent_types (list/str, optional): User agent types the rule applies to.
        block_override (bool, optional): Allow BLOCK actions to be overridden.
        ciparule (bool, optional): Enable CIPA compliance rule.
        end_user_notification_url (str, optional): URL for end user notification page.
        enforce_time_validity (bool, optional): Enforce time validity period.
        size_quota (str, optional): Size quota in KB.
        time_quota (str, optional): Time quota in minutes.
        validity_start_time (str, optional): Rule validity start time.
        validity_end_time (str, optional): Rule validity end time.
        validity_time_zone_id (str, optional): Time zone for validity dates.
        departments (list/str, optional): Department IDs the rule applies to.
        devices (list/str, optional): Device IDs the rule applies to.
        device_groups (list/str, optional): Device group IDs the rule applies to.
        groups (list/str, optional): Group IDs the rule applies to.
        labels (list/str, optional): Label IDs the rule applies to.
        locations (list/str, optional): Location IDs the rule applies to.
        location_groups (list/str, optional): Location group IDs the rule applies to.
        time_windows (list/str, optional): Time window IDs the rule applies to.
        users (list/str, optional): User IDs the rule applies to.
        workload_groups (list/str, optional): Workload group IDs the rule applies to.
        override_users (list/str, optional): User IDs that can override the rule.
        override_groups (list/str, optional): Group IDs that can override the rule.

    Returns:
        dict | list[dict] | str: Rule object(s) or status message.

    Examples:
        List all URL filtering rules:
        >>> rules = zia_url_filtering_rule_manager(action="list")

        Search for rules containing "block":
        >>> rules = zia_url_filtering_rule_manager(action="list", search="block")

        Get a specific rule:
        >>> rule = zia_url_filtering_rule_manager(action="get", rule_id="12345")

        Add a new rule:
        >>> rule = zia_url_filtering_rule_manager(
        ...     action="add",
        ...     name="Block Adult Content",
        ...     action="BLOCK",
        ...     url_categories=["OTHER_ADULT_MATERIAL"],
        ...     protocols=["ANY_RULE"],
        ...     device_trust_levels=["UNKNOWN_DEVICETRUSTLEVEL", "LOW_TRUST", "MEDIUM_TRUST", "HIGH_TRUST"]
        ... )

        Update an existing rule:
        >>> rule = zia_url_filtering_rule_manager(
        ...     action="update",
        ...     rule_id="12345",
        ...     name="Updated Rule Name",
        ...     action="ALLOW"
        ... )

        Delete a rule:
        >>> result = zia_url_filtering_rule_manager(action="delete", rule_id="12345")

    Note:
        - For list parameters, you can pass either a Python list or a JSON string.
        - The 'enabled' parameter is converted to 'state' (ENABLED/DISABLED) for the API.
        - URL categories and other ID-based parameters support both integer lists and JSON strings.
        - Override functionality only works when block_override=True and action=BLOCK.
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
            payload[param_name] = parse_list(param_value)

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

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    url = client.zia.url_filtering

    if action == "list":
        query = {"search": search} if search else {}
        rules, _, err = url.list_rules(query_params=query)
        if err:
            raise Exception(f"Failed to list URL filtering rules: {err}")
        return [r.as_dict() for r in rules]

    elif action == "get":
        if not rule_id:
            raise ValueError("rule_id is required for get.")
        rule, _, err = url.get_rule(rule_id)
        if err:
            raise Exception(f"Failed to retrieve rule {rule_id}: {err}")
        return rule.as_dict()

    elif action == "add":
        if not name or not rule_action:
            raise ValueError("name and action are required for add.")
        rule, _, err = url.add_rule(**payload)
        if err:
            raise Exception(f"Failed to add URL filtering rule: {err}")
        return rule.as_dict()

    elif action == "update":
        if not rule_id:
            raise ValueError("rule_id is required for update.")
        rule, _, err = url.update_rule(rule_id, **payload)
        if err:
            raise Exception(f"Failed to update rule {rule_id}: {err}")
        return rule.as_dict()

    elif action == "delete":
        if not rule_id:
            raise ValueError("rule_id is required for delete.")
        _, _, err = url.delete_rule(rule_id)
        if err:
            raise Exception(f"Failed to delete rule {rule_id}: {err}")
        return f"URL filtering rule {rule_id} deleted successfully."

    else:
        raise ValueError(f"Unsupported action: {action}")
