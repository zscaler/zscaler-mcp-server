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


def _build_web_dlp_rule_payload(
    name: Optional[str] = None,
    description: Optional[str] = None,
    rule_action: Optional[str] = None,
    enabled: Optional[bool] = None,
    rank: Optional[int] = None,
    order: Optional[int] = None,
    file_types: Optional[Union[List[str], str]] = None,
    min_size: Optional[str] = None,
    match_only: Optional[bool] = None,
    dlp_engines: Optional[Union[List[int], str]] = None,
    dlp_content_locations_scopes: Optional[Union[List[str], str]] = None,
    dlp_download_scan_enabled: Optional[bool] = None,
    without_content_inspection: Optional[bool] = None,
    ocr_enabled: Optional[bool] = None,
    external_auditor_email: Optional[str] = None,
    zcc_notifications_enabled: Optional[bool] = None,
    auditor: Optional[Union[List[int], str]] = None,
    cloud_applications: Optional[Union[List[int], str]] = None,
    departments: Optional[Union[List[int], str]] = None,
    excluded_groups: Optional[Union[List[int], str]] = None,
    excluded_departments: Optional[Union[List[int], str]] = None,
    excluded_users: Optional[Union[List[int], str]] = None,
    groups: Optional[Union[List[int], str]] = None,
    icap_server: Optional[Union[List[int], str]] = None,
    labels: Optional[Union[List[int], str]] = None,
    locations: Optional[Union[List[int], str]] = None,
    location_groups: Optional[Union[List[int], str]] = None,
    notification_template: Optional[Union[List[int], str]] = None,
    time_windows: Optional[Union[List[int], str]] = None,
    users: Optional[Union[List[int], str]] = None,
    url_categories: Optional[Union[List[int], str]] = None,
) -> dict:
    """Build payload for web DLP rule operations."""
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

    # File and content parameters
    if file_types is not None:
        payload["file_types"] = _parse_list(file_types)
    if min_size is not None:
        payload["min_size"] = min_size
    if match_only is not None:
        payload["match_only"] = match_only

    # DLP-specific parameters
    if dlp_content_locations_scopes is not None:
        payload["dlp_content_locations_scopes"] = _parse_list(dlp_content_locations_scopes)
    if dlp_download_scan_enabled is not None:
        payload["dlp_download_scan_enabled"] = dlp_download_scan_enabled
    if without_content_inspection is not None:
        payload["without_content_inspection"] = without_content_inspection
    if ocr_enabled is not None:
        payload["ocr_enabled"] = ocr_enabled

    # Notification parameters
    if external_auditor_email is not None:
        payload["external_auditor_email"] = external_auditor_email
    if zcc_notifications_enabled is not None:
        payload["zcc_notifications_enabled"] = zcc_notifications_enabled

    # List parameters that need parsing
    for param_name, param_value in [
        ("dlp_engines", dlp_engines),
        ("auditor", auditor),
        ("cloud_applications", cloud_applications),
        ("departments", departments),
        ("excluded_groups", excluded_groups),
        ("excluded_departments", excluded_departments),
        ("excluded_users", excluded_users),
        ("groups", groups),
        ("icap_server", icap_server),
        ("labels", labels),
        ("locations", locations),
        ("location_groups", location_groups),
        ("notification_template", notification_template),
        ("time_windows", time_windows),
        ("users", users),
        ("url_categories", url_categories),
    ]:
        if param_value is not None:
            payload[param_name] = _parse_list(param_value)

    return payload


# ============================================================================
# READ OPERATIONS (Read-Only)
# ============================================================================

def zia_list_web_dlp_rules(
    search: Annotated[
        Optional[str], Field(description="Optional search filter for listing rules by name.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[dict]:
    """
    Lists all ZIA Web DLP Rules with optional search filtering.
    This is a read-only operation.

    Web DLP Rules control and monitor data transmission based on file types,
    content patterns, DLP engines, and other criteria.

    Args:
        search (str, optional): Search string for filtering rules by name.
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "zia").

    Returns:
        list[dict]: List of web DLP rule objects.

    Example:
        List all rules:
        >>> rules = zia_list_web_dlp_rules()

        Search for rules containing "block":
        >>> rules = zia_list_web_dlp_rules(search="block")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    dlp = client.zia.dlp_web_rules

    query = {"search": search} if search else {}
    rules, _, err = dlp.list_rules(query_params=query)
    if err:
        raise Exception(f"Failed to list web DLP rules: {err}")
    return [r.as_dict() for r in rules]


def zia_list_web_dlp_rules_lite(
    search: Annotated[
        Optional[str], Field(description="Optional search filter for listing rules by name.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[dict]:
    """
    Lists all ZIA Web DLP Rules with only name and ID (lite version for faster retrieval).
    This is a read-only operation.

    Args:
        search (str, optional): Search string for filtering rules by name.
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "zia").

    Returns:
        list[dict]: List of web DLP rule objects (name and ID only).

    Example:
        List rules with name and ID only:
        >>> rules = zia_list_web_dlp_rules_lite()
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    dlp = client.zia.dlp_web_rules

    query = {"search": search} if search else {}
    rules, _, err = dlp.list_rules_lite(query_params=query)
    if err:
        raise Exception(f"Failed to list web DLP rules (lite): {err}")
    return [r.as_dict() for r in rules]


def zia_get_web_dlp_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the web DLP rule to retrieve.")
    ],
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Gets a specific ZIA Web DLP Rule by ID.
    This is a read-only operation.

    Args:
        rule_id (int/str): The ID of the web DLP rule to retrieve.
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "zia").

    Returns:
        dict: The web DLP rule object.

    Example:
        Get a specific rule:
        >>> rule = zia_get_web_dlp_rule(rule_id="12345")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    dlp = client.zia.dlp_web_rules

    rule, _, err = dlp.get_rule(rule_id)
    if err:
        raise Exception(f"Failed to retrieve rule {rule_id}: {err}")
    return rule.as_dict()


# ============================================================================
# WRITE OPERATIONS (Require --enable-write-tools flag)
# ============================================================================

def zia_create_web_dlp_rule(
    name: Annotated[str, Field(description="Rule name (required).")],
    rule_action: Annotated[
        str,
        Field(description="Action for the rule. Values: ALLOW, BLOCK, BLOCK_ICMP, BLOCK_RESET, INSPECT")
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
    file_types: Annotated[
        Optional[Union[List[str], str]],
        Field(description="List of file types the DLP policy rule applies to. Accepts JSON string or list.")
    ] = None,
    min_size: Annotated[
        Optional[str], Field(description="Minimum file size (in KB) for DLP policy rule evaluation.")
    ] = None,
    match_only: Annotated[
        Optional[bool], Field(description="If true, matches file size for DLP policy rule evaluation.")
    ] = None,
    dlp_engines: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for DLP engines this rule applies to.")
    ] = None,
    dlp_content_locations_scopes: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Specifies one or more content locations. Accepts JSON string or list.")
    ] = None,
    dlp_download_scan_enabled: Annotated[
        Optional[bool], Field(description="True enables DLP scan for file downloads.")
    ] = None,
    without_content_inspection: Annotated[
        Optional[bool], Field(description="True indicates a DLP rule without content inspection.")
    ] = None,
    ocr_enabled: Annotated[
        Optional[bool], Field(description="True allows OCR scanning of image files.")
    ] = None,
    external_auditor_email: Annotated[
        Optional[str], Field(description="Email of an external auditor for DLP notifications.")
    ] = None,
    zcc_notifications_enabled: Annotated[
        Optional[bool], Field(description="True enables Zscaler Client Connector notification.")
    ] = None,
    auditor: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for the auditors this rule applies to.")
    ] = None,
    cloud_applications: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for cloud applications this rule applies to.")
    ] = None,
    departments: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for departments this rule applies to.")
    ] = None,
    excluded_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for excluded groups.")
    ] = None,
    excluded_departments: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for excluded departments.")
    ] = None,
    excluded_users: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for excluded users.")
    ] = None,
    groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for groups this rule applies to.")
    ] = None,
    icap_server: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for the ICAP server this rule applies to.")
    ] = None,
    labels: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for labels this rule applies to.")
    ] = None,
    locations: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for locations this rule applies to.")
    ] = None,
    location_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for location groups this rule applies to.")
    ] = None,
    notification_template: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for the notification template.")
    ] = None,
    time_windows: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for time windows this rule applies to.")
    ] = None,
    users: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for users this rule applies to.")
    ] = None,
    url_categories: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for URL categories the rule applies to.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Creates a new ZIA Web DLP Rule.
    This is a write operation that requires the --enable-write-tools flag.

    Args:
        name (str): Rule name (required).
        rule_action (str): Action for the rule. Values: ALLOW, BLOCK, BLOCK_ICMP, BLOCK_RESET, INSPECT.
        [... additional parameters as documented in function signature ...]

    Returns:
        dict: The created web DLP rule object.

    Example:
        Create a rule to block image files:
        >>> rule = zia_create_web_dlp_rule(
        ...     name="Block Image Files",
        ...     rule_action="BLOCK",
        ...     file_types=["BITMAP", "JPEG", "PNG"],
        ...     dlp_download_scan_enabled=True
        ... )
    """
    payload = _build_web_dlp_rule_payload(
        name=name,
        description=description,
        rule_action=rule_action,
        enabled=enabled,
        rank=rank,
        order=order,
        file_types=file_types,
        min_size=min_size,
        match_only=match_only,
        dlp_engines=dlp_engines,
        dlp_content_locations_scopes=dlp_content_locations_scopes,
        dlp_download_scan_enabled=dlp_download_scan_enabled,
        without_content_inspection=without_content_inspection,
        ocr_enabled=ocr_enabled,
        external_auditor_email=external_auditor_email,
        zcc_notifications_enabled=zcc_notifications_enabled,
        auditor=auditor,
        cloud_applications=cloud_applications,
        departments=departments,
        excluded_groups=excluded_groups,
        excluded_departments=excluded_departments,
        excluded_users=excluded_users,
        groups=groups,
        icap_server=icap_server,
        labels=labels,
        locations=locations,
        location_groups=location_groups,
        notification_template=notification_template,
        time_windows=time_windows,
        users=users,
        url_categories=url_categories,
    )

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    dlp = client.zia.dlp_web_rules

    rule, _, err = dlp.add_rule(**payload)
    if err:
        raise Exception(f"Failed to add web DLP rule: {err}")
    return rule.as_dict()


def zia_update_web_dlp_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the web DLP rule to update.")
    ],
    name: Annotated[
        Optional[str], Field(description="Rule name.")
    ] = None,
    description: Annotated[
        Optional[str], Field(description="Optional rule description.")
    ] = None,
    rule_action: Annotated[
        Optional[str],
        Field(description="Action for the rule. Values: ALLOW, BLOCK, BLOCK_ICMP, BLOCK_RESET, INSPECT")
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
    file_types: Annotated[
        Optional[Union[List[str], str]],
        Field(description="List of file types the DLP policy rule applies to. Accepts JSON string or list.")
    ] = None,
    min_size: Annotated[
        Optional[str], Field(description="Minimum file size (in KB) for DLP policy rule evaluation.")
    ] = None,
    match_only: Annotated[
        Optional[bool], Field(description="If true, matches file size for DLP policy rule evaluation.")
    ] = None,
    dlp_engines: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for DLP engines this rule applies to.")
    ] = None,
    dlp_content_locations_scopes: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Specifies one or more content locations. Accepts JSON string or list.")
    ] = None,
    dlp_download_scan_enabled: Annotated[
        Optional[bool], Field(description="True enables DLP scan for file downloads.")
    ] = None,
    without_content_inspection: Annotated[
        Optional[bool], Field(description="True indicates a DLP rule without content inspection.")
    ] = None,
    ocr_enabled: Annotated[
        Optional[bool], Field(description="True allows OCR scanning of image files.")
    ] = None,
    external_auditor_email: Annotated[
        Optional[str], Field(description="Email of an external auditor for DLP notifications.")
    ] = None,
    zcc_notifications_enabled: Annotated[
        Optional[bool], Field(description="True enables Zscaler Client Connector notification.")
    ] = None,
    auditor: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for the auditors this rule applies to.")
    ] = None,
    cloud_applications: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for cloud applications this rule applies to.")
    ] = None,
    departments: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for departments this rule applies to.")
    ] = None,
    excluded_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for excluded groups.")
    ] = None,
    excluded_departments: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for excluded departments.")
    ] = None,
    excluded_users: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for excluded users.")
    ] = None,
    groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for groups this rule applies to.")
    ] = None,
    icap_server: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for the ICAP server this rule applies to.")
    ] = None,
    labels: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for labels this rule applies to.")
    ] = None,
    locations: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for locations this rule applies to.")
    ] = None,
    location_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for location groups this rule applies to.")
    ] = None,
    notification_template: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for the notification template.")
    ] = None,
    time_windows: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for time windows this rule applies to.")
    ] = None,
    users: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for users this rule applies to.")
    ] = None,
    url_categories: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for URL categories the rule applies to.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Updates an existing ZIA Web DLP Rule.
    This is a write operation that requires the --enable-write-tools flag.

    Args:
        rule_id (int/str): The ID of the web DLP rule to update (required).
        [... additional parameters as documented in function signature ...]

    Returns:
        dict: The updated web DLP rule object.

    Example:
        Update a rule's action:
        >>> rule = zia_update_web_dlp_rule(
        ...     rule_id="12345",
        ...     rule_action="ALLOW",
        ...     enabled=True
        ... )
    """
    payload = _build_web_dlp_rule_payload(
        name=name,
        description=description,
        rule_action=rule_action,
        enabled=enabled,
        rank=rank,
        order=order,
        file_types=file_types,
        min_size=min_size,
        match_only=match_only,
        dlp_engines=dlp_engines,
        dlp_content_locations_scopes=dlp_content_locations_scopes,
        dlp_download_scan_enabled=dlp_download_scan_enabled,
        without_content_inspection=without_content_inspection,
        ocr_enabled=ocr_enabled,
        external_auditor_email=external_auditor_email,
        zcc_notifications_enabled=zcc_notifications_enabled,
        auditor=auditor,
        cloud_applications=cloud_applications,
        departments=departments,
        excluded_groups=excluded_groups,
        excluded_departments=excluded_departments,
        excluded_users=excluded_users,
        groups=groups,
        icap_server=icap_server,
        labels=labels,
        locations=locations,
        location_groups=location_groups,
        notification_template=notification_template,
        time_windows=time_windows,
        users=users,
        url_categories=url_categories,
    )

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    dlp = client.zia.dlp_web_rules

    rule, _, err = dlp.update_rule(rule_id, **payload)
    if err:
        raise Exception(f"Failed to update rule {rule_id}: {err}")
    return rule.as_dict()


def zia_delete_web_dlp_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the web DLP rule to delete.")
    ],
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}"
) -> str:
    """
    Deletes a ZIA Web DLP Rule by ID.
    
    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.

    Args:
        rule_id (int/str): The ID of the web DLP rule to delete.
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "zia").

    Returns:
        str: Success message confirming deletion.

    Example:
        Delete a rule:
        >>> result = zia_delete_web_dlp_rule(rule_id="12345")
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs
    
    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)
    
    confirmation_check = check_confirmation(
        "zia_delete_web_dlp_rule",
        confirmed,
        {"rule_id": str(rule_id)}
    )
    if confirmation_check:
        return confirmation_check
    
    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    dlp = client.zia.dlp_web_rules

    _, _, err = dlp.delete_rule(rule_id)
    if err:
        raise Exception(f"Failed to delete rule {rule_id}: {err}")
    return f"Web DLP rule {rule_id} deleted successfully."
