"""ZIA File Type Control Rules MCP Tools.

File Type Control rules govern how ZIA handles uploads and downloads of specific
file types (e.g. block executables, allow images, caution archive uploads).

Each action exposes its own MCP tool (`zia_list_*`, `zia_get_*`,
`zia_create_*`, `zia_update_*`, `zia_delete_*`) and a sibling
`zia_list_file_type_categories` for catalog lookups.

ZIA's File Type Control update endpoint is a PUT (full replacement) under the
hood. To keep partial updates safe, ``zia_update_file_type_control_rule``
silently backfills ``name`` and ``order`` from the existing rule when the
caller does not supply them — see ``ssl_inspection.zia_update_ssl_inspection_rule``
for the same pattern.

The ``cloud_applications`` attribute follows the policy-engine cloud-app
catalog. Friendly display names supplied by users (e.g. "OneDrive", "Google
Drive") are auto-resolved to canonical enum tokens (``ONEDRIVE``, ``GDRIVE``)
via :func:`zscaler_mcp.common.zia_helpers.resolve_cloud_applications`
before the API call.

Related Tools:
    - zia_list_cloud_app_policy: List policy-engine cloud-app enum catalog
    - zia_list_shadow_it_apps: List Shadow IT analytics catalog
    - zia_list_file_type_categories: Predefined and custom file-type catalog
"""

from typing import Annotated, Any, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath
from zscaler_mcp.common.zia_helpers import (
    RANK_FIELD_DESCRIPTION,
    apply_default_order,
    apply_default_rank,
    resolve_cloud_applications,
    validate_order,
    validate_rank,
)
from zscaler_mcp.utils.utils import parse_list

# ============================================================================
# Helper Functions
# ============================================================================


def _resolve_cloud_apps_in_place(
    cloud_applications: Optional[Union[List[str], str]],
    *,
    service: str,
) -> tuple[Optional[List[str]], Optional[dict]]:
    """Translate friendly cloud-app inputs to canonical enums.

    Returns ``(resolved_enums, audit)``. ``audit`` is ``None`` when the
    inputs were already canonical (no transformation happened) or when no
    inputs were provided.
    """
    if cloud_applications is None:
        return None, None

    parsed = parse_list(cloud_applications)
    if not parsed:
        return parsed, None

    resolved, audit = resolve_cloud_applications(
        parsed,
        scope="policy",
        service=service,
        strict=True,
    )

    transformed = False
    for original, info in audit["resolved"].items():
        enums = info["enums"]
        if info["match"] != "canonical" or [original] != enums:
            transformed = True
            break

    return resolved, (audit if transformed else None)


def _build_file_type_control_rule_payload(
    name: Optional[str] = None,
    description: Optional[str] = None,
    enabled: Optional[bool] = None,
    rank: Optional[int] = None,
    order: Optional[int] = None,
    filtering_action: Optional[str] = None,
    operation: Optional[str] = None,
    time_quota: Optional[int] = None,
    size_quota: Optional[int] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    capture_pcap: Optional[bool] = None,
    active_content: Optional[bool] = None,
    unscannable: Optional[bool] = None,
    file_types: Optional[Union[List[str], str]] = None,
    protocols: Optional[Union[List[str], str]] = None,
    cloud_applications: Optional[Union[List[str], str]] = None,
    url_categories: Optional[Union[List[str], str]] = None,
    device_trust_levels: Optional[Union[List[str], str]] = None,
    locations: Optional[Union[List[int], str]] = None,
    location_groups: Optional[Union[List[int], str]] = None,
    groups: Optional[Union[List[int], str]] = None,
    departments: Optional[Union[List[int], str]] = None,
    users: Optional[Union[List[int], str]] = None,
    time_windows: Optional[Union[List[int], str]] = None,
    labels: Optional[Union[List[int], str]] = None,
    devices: Optional[Union[List[int], str]] = None,
    device_groups: Optional[Union[List[int], str]] = None,
    zpa_app_segments: Optional[Union[List[int], str]] = None,
) -> dict:
    """Build payload for File Type Control rule operations."""
    payload: dict = {}

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
    if filtering_action is not None:
        payload["filtering_action"] = filtering_action
    if operation is not None:
        payload["operation"] = operation
    if time_quota is not None:
        payload["time_quota"] = time_quota
    if size_quota is not None:
        payload["size_quota"] = size_quota
    if min_size is not None:
        payload["min_size"] = min_size
    if max_size is not None:
        payload["max_size"] = max_size
    if capture_pcap is not None:
        payload["capture_pcap"] = capture_pcap
    if active_content is not None:
        payload["active_content"] = active_content
    if unscannable is not None:
        payload["unscannable"] = unscannable

    for param_name, param_value in [
        ("file_types", file_types),
        ("protocols", protocols),
        ("cloud_applications", cloud_applications),
        ("url_categories", url_categories),
        ("device_trust_levels", device_trust_levels),
        ("locations", locations),
        ("location_groups", location_groups),
        ("groups", groups),
        ("departments", departments),
        ("users", users),
        ("time_windows", time_windows),
        ("labels", labels),
        ("devices", devices),
        ("device_groups", device_groups),
        ("zpa_app_segments", zpa_app_segments),
    ]:
        if param_value is not None:
            payload[param_name] = parse_list(param_value)

    return payload


# ============================================================================
# READ OPERATIONS (Read-Only)
# ============================================================================


def zia_list_file_type_control_rules(
    search: Annotated[
        Optional[str], Field(description="Optional search filter for listing rules by name.")
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection of results."),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Any:
    """
    Lists ZIA File Type Control Rules.

    File Type Control rules govern how ZIA treats uploads and downloads of
    specific file types — e.g. block executables, allow images, caution
    archive uploads. This is a read-only operation. Supports JMESPath
    client-side filtering via the ``query`` parameter.

    Args:
        search (str, optional): Server-side filter on rule name.
        query (str, optional): JMESPath expression for client-side filtering.
        service (str): The service to use (default: "zia").

    Returns:
        list[dict]: File Type Control rule records.

    Examples:
        List all rules:
        >>> rules = zia_list_file_type_control_rules()

        Search by name fragment:
        >>> rules = zia_list_file_type_control_rules(search="block")

        Project just name + action via JMESPath:
        >>> rules = zia_list_file_type_control_rules(query="[].{name: name, action: filtering_action}")
    """
    client = get_zscaler_client(service=service)
    ftc = client.zia.file_type_control_rule

    query_params = {"search": search} if search else {}
    rules, _, err = ftc.list_rules(query_params=query_params)
    if err:
        raise Exception(f"Failed to list File Type Control rules: {err}")
    results = [r.as_dict() for r in (rules or [])]
    return apply_jmespath(results, query)


def zia_get_file_type_control_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the File Type Control rule to retrieve.")
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Gets a specific ZIA File Type Control Rule by ID.

    Args:
        rule_id (int/str): The ID of the rule.
        service (str): The service to use (default: "zia").

    Returns:
        dict: The File Type Control rule record.
    """
    client = get_zscaler_client(service=service)
    ftc = client.zia.file_type_control_rule

    rule, _, err = ftc.get_rule(rule_id)
    if err:
        raise Exception(f"Failed to retrieve File Type Control rule {rule_id}: {err}")
    return rule.as_dict()


def zia_list_file_type_categories(
    enums: Annotated[
        Optional[str],
        Field(
            description=(
                "Filter the file-type categories returned. Supported values: "
                "'ZSCALERDLP' (Web DLP rules with content inspection), "
                "'EXTERNALDLP' (Web DLP rules without content inspection), "
                "'FILETYPECATEGORYFORFILETYPECONTROL' (File Type Control policy)."
            )
        ),
    ] = None,
    exclude_custom_file_types: Annotated[
        Optional[bool],
        Field(description="Exclude custom (admin-defined) file types from the result."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection of results."),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Any:
    """
    Lists predefined and custom file-type categories supported by ZIA.

    Use this catalog to discover the canonical ``file_types`` enum values
    accepted by File Type Control and Web DLP rules.

    Args:
        enums (str, optional): Restrict to a specific policy category.
            Values: ``ZSCALERDLP``, ``EXTERNALDLP``, ``FILETYPECATEGORYFORFILETYPECONTROL``.
        exclude_custom_file_types (bool, optional): Exclude custom file types.
        query (str, optional): JMESPath expression for client-side filtering.
        service (str): The service to use (default: "zia").

    Returns:
        list[dict]: File-type category records.
    """
    client = get_zscaler_client(service=service)
    ftc = client.zia.file_type_control_rule

    query_params: dict = {}
    if enums is not None:
        query_params["enums"] = enums
    if exclude_custom_file_types is not None:
        query_params["exclude_custom_file_types"] = exclude_custom_file_types

    categories, _, err = ftc.list_file_type_categories(query_params=query_params or None)
    if err:
        raise Exception(f"Failed to list file-type categories: {err}")
    results = [c.as_dict() for c in (categories or [])]
    return apply_jmespath(results, query)


# ============================================================================
# WRITE OPERATIONS (Require --enable-write-tools flag)
# ============================================================================


def zia_create_file_type_control_rule(
    name: Annotated[str, Field(description="Rule name (max 31 chars).")],
    filtering_action: Annotated[
        str,
        Field(
            description=(
                "Action when traffic matches. Supported values: BLOCK, CAUTION, ALLOW."
            )
        ),
    ],
    description: Annotated[Optional[str], Field(description="Optional rule description.")] = None,
    enabled: Annotated[Optional[bool], Field(description="True to enable, False to disable.")] = True,
    rank: Annotated[Optional[int], Field(description=RANK_FIELD_DESCRIPTION)] = None,
    order: Annotated[Optional[int], Field(description="Rule order; defaults to bottom.")] = None,
    operation: Annotated[
        Optional[str],
        Field(description="File operation covered by the rule (e.g. UPLOAD, DOWNLOAD)."),
    ] = None,
    time_quota: Annotated[
        Optional[int], Field(description="Time quota in minutes after which the policy applies.")
    ] = None,
    size_quota: Annotated[
        Optional[int], Field(description="Size quota in KB beyond which the policy applies.")
    ] = None,
    min_size: Annotated[Optional[int], Field(description="Minimum file size (KB) for evaluation.")] = None,
    max_size: Annotated[Optional[int], Field(description="Maximum file size (KB) for evaluation.")] = None,
    capture_pcap: Annotated[
        Optional[bool], Field(description="Enable packet capture (PCAP) for this rule.")
    ] = None,
    active_content: Annotated[
        Optional[bool],
        Field(description="If True, evaluate whether files contain active content."),
    ] = None,
    unscannable: Annotated[
        Optional[bool], Field(description="If True, treat unscannable files as a match.")
    ] = None,
    file_types: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "File types to which the rule applies. Use ``zia_list_file_type_categories`` "
                "to discover canonical values. Accepts JSON string or list."
            )
        ),
    ] = None,
    protocols: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Protocols covered by the rule. Accepts JSON string or list."),
    ] = None,
    cloud_applications: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Cloud applications the rule applies to. Accepts EITHER canonical "
                "ZIA enum tokens (e.g. 'ONEDRIVE', 'DROPBOX') OR friendly display "
                "names ('OneDrive', 'Dropbox') — friendly names are auto-resolved "
                "via the policy-engine cloud-app catalog. Accepts JSON string or list."
            )
        ),
    ] = None,
    url_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(description="URL categories the rule applies to. Accepts JSON string or list."),
    ] = None,
    device_trust_levels: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Device trust levels. Values: ANY, UNKNOWN_DEVICETRUSTLEVEL, "
                "LOW_TRUST, MEDIUM_TRUST, HIGH_TRUST. Accepts JSON string or list."
            )
        ),
    ] = None,
    locations: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for locations the rule applies to."),
    ] = None,
    location_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for location groups.")
    ] = None,
    groups: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for user groups the rule applies to."),
    ] = None,
    departments: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for departments the rule applies to."),
    ] = None,
    users: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for users the rule applies to.")
    ] = None,
    time_windows: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for time windows.")
    ] = None,
    labels: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for labels.")
    ] = None,
    devices: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for devices managed by Zscaler Client Connector."),
    ] = None,
    device_groups: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for device groups."),
    ] = None,
    zpa_app_segments: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for ZPA application segments."),
    ] = None,
    resolve_cloud_apps: Annotated[
        bool,
        Field(
            description=(
                "When True (default), friendly cloud-application names are "
                "resolved to canonical ZIA enum tokens via the policy-engine "
                "cloud-app catalog. Set False to pass cloud_applications "
                "through unchanged (advanced)."
            )
        ),
    ] = True,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Creates a ZIA File Type Control Rule.

    This is a write operation that requires the ``--enable-write-tools`` flag.

    Returns:
        dict: The created File Type Control rule. If friendly cloud-app names
        were resolved, ``_cloud_applications_resolution`` is included for audit.
    """
    cloud_apps_audit: Optional[dict] = None
    if resolve_cloud_apps and cloud_applications is not None:
        cloud_applications, cloud_apps_audit = _resolve_cloud_apps_in_place(
            cloud_applications, service=service
        )

    rank = apply_default_rank(rank)
    order = apply_default_order(order)
    payload = _build_file_type_control_rule_payload(
        name=name,
        description=description,
        enabled=enabled,
        rank=rank,
        order=order,
        filtering_action=filtering_action,
        operation=operation,
        time_quota=time_quota,
        size_quota=size_quota,
        min_size=min_size,
        max_size=max_size,
        capture_pcap=capture_pcap,
        active_content=active_content,
        unscannable=unscannable,
        file_types=file_types,
        protocols=protocols,
        cloud_applications=cloud_applications,
        url_categories=url_categories,
        device_trust_levels=device_trust_levels,
        locations=locations,
        location_groups=location_groups,
        groups=groups,
        departments=departments,
        users=users,
        time_windows=time_windows,
        labels=labels,
        devices=devices,
        device_groups=device_groups,
        zpa_app_segments=zpa_app_segments,
    )

    client = get_zscaler_client(service=service)
    ftc = client.zia.file_type_control_rule

    rule, _, err = ftc.add_rule(**payload)
    if err:
        raise Exception(f"Failed to create File Type Control rule: {err}")
    result = rule.as_dict()
    if cloud_apps_audit:
        result["_cloud_applications_resolution"] = cloud_apps_audit
    return result


def zia_update_file_type_control_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the File Type Control rule to update.")
    ],
    name: Annotated[Optional[str], Field(description="Rule name (max 31 chars).")] = None,
    description: Annotated[Optional[str], Field(description="Optional rule description.")] = None,
    enabled: Annotated[Optional[bool], Field(description="True to enable, False to disable.")] = None,
    rank: Annotated[Optional[int], Field(description=RANK_FIELD_DESCRIPTION)] = None,
    order: Annotated[Optional[int], Field(description="Rule order; defaults to bottom.")] = None,
    filtering_action: Annotated[
        Optional[str],
        Field(description="Action when traffic matches. Values: BLOCK, CAUTION, ALLOW."),
    ] = None,
    operation: Annotated[
        Optional[str],
        Field(description="File operation covered by the rule (e.g. UPLOAD, DOWNLOAD)."),
    ] = None,
    time_quota: Annotated[Optional[int], Field(description="Time quota in minutes.")] = None,
    size_quota: Annotated[Optional[int], Field(description="Size quota in KB.")] = None,
    min_size: Annotated[Optional[int], Field(description="Minimum file size (KB).")] = None,
    max_size: Annotated[Optional[int], Field(description="Maximum file size (KB).")] = None,
    capture_pcap: Annotated[Optional[bool], Field(description="Enable PCAP.")] = None,
    active_content: Annotated[
        Optional[bool], Field(description="Match files containing active content.")
    ] = None,
    unscannable: Annotated[
        Optional[bool], Field(description="Match unscannable files.")
    ] = None,
    file_types: Annotated[
        Optional[Union[List[str], str]],
        Field(description="File types the rule applies to. Accepts JSON string or list."),
    ] = None,
    protocols: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Protocols. Accepts JSON string or list."),
    ] = None,
    cloud_applications: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Cloud applications. Accepts canonical enums OR friendly display "
                "names — friendly names are auto-resolved. Accepts JSON string or list."
            )
        ),
    ] = None,
    url_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(description="URL categories. Accepts JSON string or list."),
    ] = None,
    device_trust_levels: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Device trust levels. Accepts JSON string or list."),
    ] = None,
    locations: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for locations.")
    ] = None,
    location_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for location groups.")
    ] = None,
    groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for user groups.")
    ] = None,
    departments: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for departments.")
    ] = None,
    users: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for users.")
    ] = None,
    time_windows: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for time windows.")
    ] = None,
    labels: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for labels.")
    ] = None,
    devices: Annotated[
        Optional[Union[List[int], str]],
        Field(description="IDs for devices managed by Zscaler Client Connector."),
    ] = None,
    device_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for device groups.")
    ] = None,
    zpa_app_segments: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for ZPA app segments.")
    ] = None,
    resolve_cloud_apps: Annotated[
        bool,
        Field(
            description=(
                "When True (default), friendly cloud-application names are resolved "
                "to canonical enums. Set False to pass values through unchanged."
            )
        ),
    ] = True,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Updates a ZIA File Type Control Rule.

    This is a write operation that requires the ``--enable-write-tools`` flag.

    The ZIA File Type Control update endpoint is a PUT (full replacement)
    under the hood, so payloads missing the required ``name`` and ``order``
    identifiers are rejected. This tool silently backfills those two fields
    from the existing rule when the caller does not supply them, allowing
    safe partial updates without exposing the merge as a user-facing knob.

    Returns:
        dict: The updated File Type Control rule. If friendly cloud-app names
        were resolved, ``_cloud_applications_resolution`` is included for audit.
    """
    cloud_apps_audit: Optional[dict] = None
    if resolve_cloud_apps and cloud_applications is not None:
        cloud_applications, cloud_apps_audit = _resolve_cloud_apps_in_place(
            cloud_applications, service=service
        )

    if rank is not None:
        rank = validate_rank(rank)
    if order is not None:
        order = validate_order(order)
    payload = _build_file_type_control_rule_payload(
        name=name,
        description=description,
        enabled=enabled,
        rank=rank,
        order=order,
        filtering_action=filtering_action,
        operation=operation,
        time_quota=time_quota,
        size_quota=size_quota,
        min_size=min_size,
        max_size=max_size,
        capture_pcap=capture_pcap,
        active_content=active_content,
        unscannable=unscannable,
        file_types=file_types,
        protocols=protocols,
        cloud_applications=cloud_applications,
        url_categories=url_categories,
        device_trust_levels=device_trust_levels,
        locations=locations,
        location_groups=location_groups,
        groups=groups,
        departments=departments,
        users=users,
        time_windows=time_windows,
        labels=labels,
        devices=devices,
        device_groups=device_groups,
        zpa_app_segments=zpa_app_segments,
    )

    client = get_zscaler_client(service=service)
    ftc = client.zia.file_type_control_rule

    if "name" not in payload or "order" not in payload:
        existing, _, fetch_err = ftc.get_rule(rule_id)
        if fetch_err:
            raise Exception(
                f"Failed to fetch File Type Control rule {rule_id} for required-field backfill: {fetch_err}"
            )
        existing_dict = existing.as_dict()
        payload.setdefault("name", existing_dict.get("name"))
        payload.setdefault("order", existing_dict.get("order"))

    rule, _, err = ftc.update_rule(rule_id, **payload)
    if err:
        raise Exception(f"Failed to update File Type Control rule {rule_id}: {err}")
    result = rule.as_dict()
    if cloud_apps_audit:
        result["_cloud_applications_resolution"] = cloud_apps_audit
    return result


def zia_delete_file_type_control_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the File Type Control rule to delete.")
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}",
) -> str:
    """
    Deletes a ZIA File Type Control Rule by ID.

    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.

    Returns:
        str: Success message confirming deletion.
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs

    confirmed = extract_confirmed_from_kwargs(kwargs)
    confirmation_check = check_confirmation(
        "zia_delete_file_type_control_rule", confirmed, {"rule_id": str(rule_id)}
    )
    if confirmation_check:
        return confirmation_check

    client = get_zscaler_client(service=service)
    ftc = client.zia.file_type_control_rule

    _, _, err = ftc.delete_rule(rule_id)
    if err:
        raise Exception(f"Failed to delete File Type Control rule {rule_id}: {err}")
    return f"File Type Control rule {rule_id} deleted successfully."
