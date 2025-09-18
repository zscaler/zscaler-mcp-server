import json
from typing import Annotated, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zia_web_dlp_rule_manager(
    action: Annotated[
        Literal["read", "read_lite", "create", "update", "delete"],
        Field(
            description="Web DLP rule operation: read, read_lite, create, update, or delete."
        ),
    ] = "read",
    rule_id: Annotated[
        Optional[Union[int, str]],
        Field(description="Required for read, update, and delete operations."),
    ] = None,
    name: Annotated[
        Optional[str], Field(description="Rule name (required for add/update).")
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
    # File and content parameters
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
    # DLP-specific parameters
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
    # Notification parameters
    external_auditor_email: Annotated[
        Optional[str], Field(description="Email of an external auditor for DLP notifications.")
    ] = None,
    zcc_notifications_enabled: Annotated[
        Optional[bool], Field(description="True enables Zscaler Client Connector notification.")
    ] = None,
    # ID-based parameters (can be passed as JSON string or list)
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
) -> Union[dict, List[dict], str]:
    """
    Manages ZIA Web DLP Rules for controlling data loss prevention policies on web traffic.

    Web DLP Rules allow you to control and monitor data transmission based on file types,
    content patterns, DLP engines, and other criteria. Rules can be configured to allow,
    block, or inspect traffic for potential data loss prevention violations.

    Args:
        action (str): Operation to perform: read, read_lite, create, update, or delete.
        rule_id (int/str, optional): Required for read, update, and delete operations.
        name (str, optional): Rule name (required for add/update).
        description (str, optional): Optional rule description.
        action (str, optional): Action for the rule. Values: ALLOW, BLOCK, BLOCK_ICMP, BLOCK_RESET, INSPECT.
        enabled (bool, optional): True to enable rule, False to disable (default: True).
        search (str, optional): Search string for filtering rules by name.
        rank (int, optional): Admin rank of the rule.
        order (int, optional): Rule order, defaults to the bottom.
        file_types (list/str, optional): List of file types the DLP policy rule applies to.
        min_size (str, optional): Minimum file size (in KB) for DLP policy rule evaluation.
        match_only (bool, optional): If true, matches file size for DLP policy rule evaluation.
        dlp_engines (list/str, optional): IDs for DLP engines this rule applies to.
        dlp_content_locations_scopes (list/str, optional): Specifies one or more content locations.
        dlp_download_scan_enabled (bool, optional): True enables DLP scan for file downloads.
        without_content_inspection (bool, optional): True indicates a DLP rule without content inspection.
        ocr_enabled (bool, optional): True allows OCR scanning of image files.
        external_auditor_email (str, optional): Email of an external auditor for DLP notifications.
        zcc_notifications_enabled (bool, optional): True enables Zscaler Client Connector notification.
        auditor (list/str, optional): IDs for the auditors this rule applies to.
        cloud_applications (list/str, optional): IDs for cloud applications this rule applies to.
        departments (list/str, optional): Department IDs the rule applies to.
        excluded_groups (list/str, optional): Excluded group IDs.
        excluded_departments (list/str, optional): Excluded department IDs.
        excluded_users (list/str, optional): Excluded user IDs.
        groups (list/str, optional): Group IDs the rule applies to.
        icap_server (list/str, optional): ICAP server IDs the rule applies to.
        labels (list/str, optional): Label IDs the rule applies to.
        locations (list/str, optional): Location IDs the rule applies to.
        location_groups (list/str, optional): Location group IDs the rule applies to.
        notification_template (list/str, optional): Notification template IDs.
        time_windows (list/str, optional): Time window IDs the rule applies to.
        users (list/str, optional): User IDs the rule applies to.
        url_categories (list/str, optional): URL category IDs the rule applies to.

    Returns:
        dict | list[dict] | str: Rule object(s) or status message.

    Examples:
        List all web DLP rules:
        >>> rules = zia_web_dlp_rule_manager(action="read")

        List rules with name and ID only:
        >>> rules = zia_web_dlp_rule_manager(action="read_lite")

        Search for rules containing "block":
        >>> rules = zia_web_dlp_rule_manager(action="read", search="block")

        Get a specific rule:
        >>> rule = zia_web_dlp_rule_manager(action="read", rule_id="12345")

        Add a new rule to block image files:
        >>> rule = zia_web_dlp_rule_manager(
        ...     action="create",
        ...     name="Block Image Files",
        ...     action="BLOCK",
        ...     file_types=["BITMAP", "JPEG", "PNG"],
        ...     dlp_download_scan_enabled=True,
        ...     min_size="100"
        ... )

        Add a rule to allow specific file types for Finance group:
        >>> rule = zia_web_dlp_rule_manager(
        ...     action="create",
        ...     name="Allow Finance Documents",
        ...     action="ALLOW",
        ...     file_types=["PDF", "DOC", "DOCX", "XLS", "XLSX"],
        ...     groups=["95016183"],
        ...     description="Allow finance documents for finance group"
        ... )

        Update an existing rule:
        >>> rule = zia_web_dlp_rule_manager(
        ...     action="update",
        ...     rule_id="12345",
        ...     name="Updated Rule Name",
        ...     action="BLOCK"
        ... )

        Delete a rule:
        >>> result = zia_web_dlp_rule_manager(action="delete", rule_id="12345")

    Note:
        - For list parameters, you can pass either a Python list or a JSON string.
        - The 'enabled' parameter is converted to 'state' (ENABLED/DISABLED) for the API.
        - File types should be specified as strings (e.g., "PDF", "DOC", "JPEG").
        - DLP engines, groups, and other ID-based parameters support both integer lists and JSON strings.
        - The list_lite action returns only name and ID information for faster retrieval.
        - OCR scanning is only applicable to image file types.
        - External auditor email is used for DLP violation notifications.
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

    # File and content parameters
    if file_types is not None:
        payload["file_types"] = parse_list(file_types)
    if min_size is not None:
        payload["min_size"] = min_size
    if match_only is not None:
        payload["match_only"] = match_only

    # DLP-specific parameters
    if dlp_content_locations_scopes is not None:
        payload["dlp_content_locations_scopes"] = parse_list(dlp_content_locations_scopes)
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
            payload[param_name] = parse_list(param_value)

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    dlp = client.zia.dlp_web_rules

    if action == "read":
        if rule_id:
            # Get specific rule by ID
            rule, _, err = dlp.get_rule(rule_id)
            if err:
                raise Exception(f"Failed to retrieve rule {rule_id}: {err}")
            return rule.as_dict()
        else:
            # List all rules
            query = {"search": search} if search else {}
            rules, _, err = dlp.list_rules(query_params=query)
            if err:
                raise Exception(f"Failed to list web DLP rules: {err}")
            return [r.as_dict() for r in rules]

    elif action == "read_lite":
        query = {"search": search} if search else {}
        rules, _, err = dlp.list_rules_lite(query_params=query)
        if err:
            raise Exception(f"Failed to list web DLP rules (lite): {err}")
        return [r.as_dict() for r in rules]

    elif action == "create":
        if not name or not rule_action:
            raise ValueError("name and action are required for add.")
        rule, _, err = dlp.add_rule(**payload)
        if err:
            raise Exception(f"Failed to add web DLP rule: {err}")
        return rule.as_dict()

    elif action == "update":
        if not rule_id:
            raise ValueError("rule_id is required for update.")
        rule, _, err = dlp.update_rule(rule_id, **payload)
        if err:
            raise Exception(f"Failed to update rule {rule_id}: {err}")
        return rule.as_dict()

    elif action == "delete":
        if not rule_id:
            raise ValueError("rule_id is required for delete.")
        _, _, err = dlp.delete_rule(rule_id)
        if err:
            raise Exception(f"Failed to delete rule {rule_id}: {err}")
        return f"Web DLP rule {rule_id} deleted successfully."

    else:
        raise ValueError(f"Unsupported action: {action}")
