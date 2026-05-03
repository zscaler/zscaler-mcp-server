"""ZIA Sandbox Rules MCP Tools.

Sandbox rules govern how the ZIA Sandbox handles unknown or suspicious files
(allow scan, block, threshold-based actions, ML "Instant Verdict", etc.).
These are policy rules — distinct from the sandbox *report/quota* tools in
``zscaler_mcp/tools/zia/get_sandbox_info.py`` which query sandbox findings.

Each action is exposed as its own MCP tool: ``zia_list_*``, ``zia_get_*``,
``zia_create_*``, ``zia_update_*``, ``zia_delete_*``.

ZIA's Sandbox rule update endpoint is a PUT (full replacement). To keep
partial updates safe, ``zia_update_sandbox_rule`` silently backfills
``name`` and ``order`` from the existing rule when the caller does not
supply them.
"""

from typing import Annotated, Any, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath
from zscaler_mcp.common.zia_helpers import (
    RANK_FIELD_DESCRIPTION,
    apply_default_order,
    apply_default_rank,
    validate_order,
    validate_rank,
)
from zscaler_mcp.utils.utils import parse_list

# ============================================================================
# Helper Functions
# ============================================================================


def _build_sandbox_rule_payload(
    name: Optional[str] = None,
    description: Optional[str] = None,
    enabled: Optional[bool] = None,
    rank: Optional[int] = None,
    order: Optional[int] = None,
    ba_rule_action: Optional[str] = None,
    first_time_enable: Optional[bool] = None,
    first_time_operation: Optional[str] = None,
    ml_action_enabled: Optional[bool] = None,
    by_threat_score: Optional[int] = None,
    ba_policy_categories: Optional[Union[List[str], str]] = None,
    file_types: Optional[Union[List[str], str]] = None,
    protocols: Optional[Union[List[str], str]] = None,
    url_categories: Optional[Union[List[str], str]] = None,
    groups: Optional[Union[List[int], str]] = None,
    departments: Optional[Union[List[int], str]] = None,
    users: Optional[Union[List[int], str]] = None,
    locations: Optional[Union[List[int], str]] = None,
    location_groups: Optional[Union[List[int], str]] = None,
    labels: Optional[Union[List[int], str]] = None,
    time_windows: Optional[Union[List[int], str]] = None,
) -> dict:
    """Build payload for Sandbox rule operations."""
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
    if ba_rule_action is not None:
        payload["ba_rule_action"] = ba_rule_action
    if first_time_enable is not None:
        payload["first_time_enable"] = first_time_enable
    if first_time_operation is not None:
        payload["first_time_operation"] = first_time_operation
    if ml_action_enabled is not None:
        payload["ml_action_enabled"] = ml_action_enabled
    if by_threat_score is not None:
        payload["by_threat_score"] = by_threat_score

    for param_name, param_value in [
        ("ba_policy_categories", ba_policy_categories),
        ("file_types", file_types),
        ("protocols", protocols),
        ("url_categories", url_categories),
        ("groups", groups),
        ("departments", departments),
        ("users", users),
        ("locations", locations),
        ("location_groups", location_groups),
        ("labels", labels),
        ("time_windows", time_windows),
    ]:
        if param_value is not None:
            payload[param_name] = parse_list(param_value)

    return payload


# ============================================================================
# READ OPERATIONS (Read-Only)
# ============================================================================


def zia_list_sandbox_rules(
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
    Lists ZIA Sandbox Rules.

    Sandbox rules govern how the ZIA Sandbox handles unknown or suspicious
    files (allow scan, block, threshold-based actions, ML "Instant
    Verdict", etc.). This is a read-only operation. Supports JMESPath
    client-side filtering via the ``query`` parameter.

    Returns:
        list[dict]: Sandbox rule records.
    """
    client = get_zscaler_client(service=service)
    sb = client.zia.sandbox_rules

    query_params = {"search": search} if search else {}
    rules, _, err = sb.list_rules(query_params=query_params)
    if err:
        raise Exception(f"Failed to list Sandbox rules: {err}")
    results = [r.as_dict() for r in (rules or [])]
    return apply_jmespath(results, query)


def zia_get_sandbox_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the Sandbox rule to retrieve.")
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Gets a specific ZIA Sandbox Rule by ID.

    Returns:
        dict: The Sandbox rule record.
    """
    client = get_zscaler_client(service=service)
    sb = client.zia.sandbox_rules

    rule, _, err = sb.get_rule(rule_id)
    if err:
        raise Exception(f"Failed to retrieve Sandbox rule {rule_id}: {err}")
    return rule.as_dict()


# ============================================================================
# WRITE OPERATIONS (Require --enable-write-tools flag)
# ============================================================================


def zia_create_sandbox_rule(
    name: Annotated[str, Field(description="Rule name (max 31 chars).")],
    ba_rule_action: Annotated[
        str,
        Field(
            description=(
                "Behavioural Analysis action when traffic matches "
                "(e.g. ALLOW, BLOCK)."
            )
        ),
    ],
    description: Annotated[Optional[str], Field(description="Optional rule description.")] = None,
    enabled: Annotated[Optional[bool], Field(description="True to enable, False to disable.")] = True,
    rank: Annotated[Optional[int], Field(description=RANK_FIELD_DESCRIPTION)] = None,
    order: Annotated[Optional[int], Field(description="Rule order; defaults to bottom.")] = None,
    first_time_enable: Annotated[
        Optional[bool],
        Field(description="Enable a First-Time action specifically for this rule."),
    ] = None,
    first_time_operation: Annotated[
        Optional[str],
        Field(
            description=(
                "Action when users download unknown files for the first time "
                "(e.g. ALLOW_SCAN, BLOCK)."
            )
        ),
    ] = None,
    ml_action_enabled: Annotated[
        Optional[bool],
        Field(description="Enable AI Instant Verdict for unknown files."),
    ] = None,
    by_threat_score: Annotated[
        Optional[int],
        Field(description="Minimum threat score (40-70) that triggers this rule."),
    ] = None,
    ba_policy_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Behavioural-analysis policy categories the rule applies to "
                "(e.g. ADWARE_BLOCK, RANSOMWARE_BLOCK). Accepts JSON string or list."
            )
        ),
    ] = None,
    file_types: Annotated[
        Optional[Union[List[str], str]],
        Field(description="File types covered by the rule. Accepts JSON string or list."),
    ] = None,
    protocols: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Protocols the rule applies to. Accepts JSON string or list."),
    ] = None,
    url_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(description="URL categories covered. Accepts JSON string or list."),
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
    locations: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for locations.")
    ] = None,
    location_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for location groups.")
    ] = None,
    labels: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for labels.")
    ] = None,
    time_windows: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for time windows.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Creates a ZIA Sandbox Rule.

    This is a write operation that requires the ``--enable-write-tools`` flag.

    Returns:
        dict: The created Sandbox rule.
    """
    rank = apply_default_rank(rank)
    order = apply_default_order(order)
    payload = _build_sandbox_rule_payload(
        name=name,
        description=description,
        enabled=enabled,
        rank=rank,
        order=order,
        ba_rule_action=ba_rule_action,
        first_time_enable=first_time_enable,
        first_time_operation=first_time_operation,
        ml_action_enabled=ml_action_enabled,
        by_threat_score=by_threat_score,
        ba_policy_categories=ba_policy_categories,
        file_types=file_types,
        protocols=protocols,
        url_categories=url_categories,
        groups=groups,
        departments=departments,
        users=users,
        locations=locations,
        location_groups=location_groups,
        labels=labels,
        time_windows=time_windows,
    )

    client = get_zscaler_client(service=service)
    sb = client.zia.sandbox_rules

    rule, _, err = sb.add_rule(**payload)
    if err:
        raise Exception(f"Failed to create Sandbox rule: {err}")
    return rule.as_dict()


def zia_update_sandbox_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the Sandbox rule to update.")
    ],
    name: Annotated[Optional[str], Field(description="Rule name (max 31 chars).")] = None,
    description: Annotated[Optional[str], Field(description="Optional rule description.")] = None,
    enabled: Annotated[Optional[bool], Field(description="True to enable, False to disable.")] = None,
    rank: Annotated[Optional[int], Field(description=RANK_FIELD_DESCRIPTION)] = None,
    order: Annotated[Optional[int], Field(description="Rule order.")] = None,
    ba_rule_action: Annotated[
        Optional[str],
        Field(description="Behavioural Analysis action."),
    ] = None,
    first_time_enable: Annotated[
        Optional[bool], Field(description="Enable First-Time action.")
    ] = None,
    first_time_operation: Annotated[
        Optional[str], Field(description="Operation for first-time action.")
    ] = None,
    ml_action_enabled: Annotated[
        Optional[bool], Field(description="Enable AI Instant Verdict.")
    ] = None,
    by_threat_score: Annotated[
        Optional[int], Field(description="Minimum threat score (40-70).")
    ] = None,
    ba_policy_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Behavioural-analysis policy categories. Accepts JSON string or list."),
    ] = None,
    file_types: Annotated[
        Optional[Union[List[str], str]],
        Field(description="File types. Accepts JSON string or list."),
    ] = None,
    protocols: Annotated[
        Optional[Union[List[str], str]],
        Field(description="Protocols. Accepts JSON string or list."),
    ] = None,
    url_categories: Annotated[
        Optional[Union[List[str], str]],
        Field(description="URL categories. Accepts JSON string or list."),
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
    locations: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for locations.")
    ] = None,
    location_groups: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for location groups.")
    ] = None,
    labels: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for labels.")
    ] = None,
    time_windows: Annotated[
        Optional[Union[List[int], str]], Field(description="IDs for time windows.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Updates a ZIA Sandbox Rule.

    This is a write operation that requires the ``--enable-write-tools`` flag.

    The Sandbox rule update endpoint is a PUT (full replacement). This tool
    silently backfills ``name`` and ``order`` from the existing rule when
    the caller does not supply them, so partial updates "just work".

    Returns:
        dict: The updated Sandbox rule.
    """
    if rank is not None:
        rank = validate_rank(rank)
    if order is not None:
        order = validate_order(order)
    payload = _build_sandbox_rule_payload(
        name=name,
        description=description,
        enabled=enabled,
        rank=rank,
        order=order,
        ba_rule_action=ba_rule_action,
        first_time_enable=first_time_enable,
        first_time_operation=first_time_operation,
        ml_action_enabled=ml_action_enabled,
        by_threat_score=by_threat_score,
        ba_policy_categories=ba_policy_categories,
        file_types=file_types,
        protocols=protocols,
        url_categories=url_categories,
        groups=groups,
        departments=departments,
        users=users,
        locations=locations,
        location_groups=location_groups,
        labels=labels,
        time_windows=time_windows,
    )

    client = get_zscaler_client(service=service)
    sb = client.zia.sandbox_rules

    if "name" not in payload or "order" not in payload:
        existing, _, fetch_err = sb.get_rule(rule_id)
        if fetch_err:
            raise Exception(
                f"Failed to fetch Sandbox rule {rule_id} for required-field backfill: {fetch_err}"
            )
        existing_dict = existing.as_dict()
        payload.setdefault("name", existing_dict.get("name"))
        payload.setdefault("order", existing_dict.get("order"))

    rule, _, err = sb.update_rule(rule_id, **payload)
    if err:
        raise Exception(f"Failed to update Sandbox rule {rule_id}: {err}")
    return rule.as_dict()


def zia_delete_sandbox_rule(
    rule_id: Annotated[
        Union[int, str], Field(description="The ID of the Sandbox rule to delete.")
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}",
) -> str:
    """
    Deletes a ZIA Sandbox Rule by ID.

    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.

    Returns:
        str: Success message confirming deletion.
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs

    confirmed = extract_confirmed_from_kwargs(kwargs)
    confirmation_check = check_confirmation(
        "zia_delete_sandbox_rule", confirmed, {"rule_id": str(rule_id)}
    )
    if confirmation_check:
        return confirmation_check

    client = get_zscaler_client(service=service)
    sb = client.zia.sandbox_rules

    _, _, err = sb.delete_rule(rule_id)
    if err:
        raise Exception(f"Failed to delete Sandbox rule {rule_id}: {err}")
    return f"Sandbox rule {rule_id} deleted successfully."
